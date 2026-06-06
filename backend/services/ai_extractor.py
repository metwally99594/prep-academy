"""AI-powered structured question extraction via OpenRouter/DeepSeek.

Replaces the fragile regex-only parser for production imports.
Pipeline:
  1. Split document into chunks (~2000-3000 chars, with overlap)
  2. Send each chunk to DeepSeek with structured extraction prompt
  3. Parse JSON response
  4. Validate structure and content
  5. Return normalized ParsedQuestion list
"""
import os, re, json, httpx, asyncio
from typing import List, Optional
from database import logger
from models import ParsedQuestion

# Detection patterns for merged questions
_MERGED_PATTERNS = [
    re.compile(r"\n\d+[.)]\s+(?=[A-ZÄÖÜ])"),     # "2. What is..." or "2) What is..."
    re.compile(r"\n##\s*(?:Question|Frage)\b", re.IGNORECASE),  # "## Question 3"
    re.compile(r"\n[A-Z][)][ ]+(?=[A-ZÄÖÜ])"),   # "A) Text" mid-question suggests boundary
]

OR_KEY = os.environ.get("OPENROUTER_API_KEY")
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
OR_MODEL = "deepseek/deepseek-chat"
OR_HEADERS = {
    "Authorization": f"Bearer {OR_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://mcq-medical-prep.academy",
    "X-Title": "PrepAcademy",
}

CHUNK_SIZE = 3000
CHUNK_OVERLAP = 200


def chunk_document(text: str) -> List[str]:
    """Split document into overlapping chunks at natural boundaries."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len > CHUNK_SIZE and current:
            chunks.append("\n\n".join(current))
            # Keep last paragraph(s) for overlap
            overlap = []
            overlap_len = 0
            for p in reversed(current):
                if overlap_len + len(p) > CHUNK_OVERLAP:
                    break
                overlap.insert(0, p)
                overlap_len += len(p)
            current = overlap
            current_len = overlap_len
        current.append(para)
        current_len += para_len

    if current:
        chunks.append("\n\n".join(current))
    return chunks


EXTRACTION_SYSTEM_PROMPT = """You are a medical exam question extraction system. Extract ALL questions from the given exam document text.

For EACH question, extract:
- "question": The complete question text (preserve exactly, including any image references like [Image], (Image), etc.)
- "type": One of: "single", "multi", "true_false", "matching", "grouping", "image"
- "options": Array of option strings (preserve original formatting including letter prefixes like "A) ...")
- "correct_answers": Array of the EXACT option strings that are correct

Rules:
- The JSON key MUST be "question" (not "question_text" or anything else)
- Preserve question text EXACTLY as written (do not paraphrase, summarize, or modify)
- Preserve ALL options exactly as written
- Preserve correct_answers as the exact option strings (e.g. "A) Text" not just "A")
- For true/false questions: options are ["A) Richtig", "B) Falsch"]
- For matching questions: options should contain the match pairs or descriptions
- For grouping questions: each sub-question is a separate entry with the shared stem
- For image questions: preserve the image placeholder text as-is in the question text
- NEVER merge two questions into one
- NEVER let answer text leak into the next question
- If a block appears to contain multiple questions, extract each one separately
- Return ONLY valid JSON array — no markdown fences, no explanations, no extra text

Response format (strict JSON array — keys MUST be exactly "question", "type", "options", "correct_answers"):
[
  {
    "question": "Full question text here...",
    "type": "single",
    "options": ["A) Option one", "B) Option two", "C) Option three", "D) Option four", "E) Option five"],
    "correct_answers": ["A) Option one"]
  }
]"""


def _clean_json_response(content: str) -> str:
    """Strip markdown fences, <think> tags, and surrounding text to isolate JSON."""
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    content = re.sub(r"```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```", "", content)
    # Find first [ and last ]
    start = content.find("[")
    end = content.rfind("]")
    if start != -1 and end != -1 and end > start:
        content = content[start : end + 1]
    return content.strip()


async def extract_questions_from_chunk(chunk: str, chunk_index: int) -> List[dict]:
    """Send a single chunk to DeepSeek and return extracted question dicts."""
    if not OR_KEY:
        logger.error("[AI_EXTRACTOR] OPENROUTER_API_KEY not set")
        return []

    prompt = f"Extract ALL exam questions from this document chunk (chunk {chunk_index}):\n\n{chunk}"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                OR_URL,
                headers=OR_HEADERS,
                json={
                    "model": OR_MODEL,
                    "messages": [
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 4096,
                    "temperature": 0.1,
                },
            )
        d = r.json()
        content = d.get("choices", [{}])[0].get("message", {}).get("content", "")
        content = _clean_json_response(content)
        if not content:
            logger.warning(f"[AI_EXTRACTOR] Empty response for chunk {chunk_index}")
            return []

        questions = json.loads(content)
        if not isinstance(questions, list):
            logger.warning(f"[AI_EXTRACTOR] Response not a list for chunk {chunk_index}")
            return []

        return questions

    except json.JSONDecodeError as e:
        logger.error(f"[AI_EXTRACTOR] JSON parse error in chunk {chunk_index}: {e}")
        logger.debug(f"Raw content: {content[:500]}")
        return []
    except httpx.TimeoutException:
        logger.error(f"[AI_EXTRACTOR] Timeout for chunk {chunk_index}")
        return []
    except Exception as e:
        logger.error(f"[AI_EXTRACTOR] Error processing chunk {chunk_index}: {e}")
        return []


def _detect_merge_indicators(text: str) -> list:
    """Check for patterns suggesting a single entry contains multiple questions."""
    indicators = []
    for pat in _MERGED_PATTERNS:
        matches = pat.findall(text)
        if matches:
            indicators.append(matches)
    # Multiple question marks in one entry
    qmarks = [m.start() for m in re.finditer(r"\?", text)]
    if len(qmarks) > 1:
        indicators.append(f"multiple_question_marks({len(qmarks)})")
    return indicators


def validate_extracted_question(q: dict, index: int) -> Optional[dict]:
    """Validate a single extracted question dict. Returns cleaned dict or None."""
    if not isinstance(q, dict):
        return None

    # Accept both "question" and "question_text" keys (AI sometimes returns the latter)
    question = (q.get("question") or q.get("question_text") or "").strip()
    if not question:
        logger.warning(f"[AI_EXTRACTOR] Q{index}: malformed — empty question text")
        return None

    qtype = (q.get("type") or "single").strip().lower()
    if qtype not in ("single", "multi", "true_false", "matching", "grouping", "image"):
        logger.warning(f"[AI_EXTRACTOR] Q{index}: malformed — unknown type '{qtype}', defaulting to single")
        qtype = "single"

    options = q.get("options", [])
    if not isinstance(options, list):
        options = []
    options = [str(o).strip() for o in options if str(o).strip()]

    correct_answers = q.get("correct_answers", [])
    if not isinstance(correct_answers, list):
        correct_answers = []
    correct_answers = [str(ca).strip() for ca in correct_answers if str(ca).strip()]

    # Log missing answers
    if not correct_answers:
        logger.warning(f"[AI_EXTRACTOR] Q{index}: missing answers — correct_answers is empty")

    # Log missing options
    if not options:
        logger.warning(f"[AI_EXTRACTOR] Q{index}: missing options — no options provided")
    elif len(options) < 2:
        logger.warning(f"[AI_EXTRACTOR] Q{index}: too few options — got {len(options)}, expected >=2")

    # Detect possible merged questions
    merge_indicators = _detect_merge_indicators(question)
    if merge_indicators:
        logger.warning(f"[AI_EXTRACTOR] Q{index}: possible merged question — indicators: {merge_indicators}")

    # Validate correct_answers exist in options (partial match accepted)
    for ca in correct_answers:
        ca_lower = ca.lower()
        found = any(ca_lower == o.lower() or ca_lower in o.lower() or o.lower() in ca_lower for o in options)
        if not found:
            logger.warning(f"[AI_EXTRACTOR] Q{index}: correct answer '{ca}' not found in options")

    return {
        "question": question,
        "type": qtype,
        "options": options,
        "correct_answers": correct_answers,
    }


def _deduplicate_questions(questions: List[dict]) -> List[dict]:
    """Remove near-duplicate questions (same question text, different chunks)."""
    seen = set()
    unique = []
    for q in questions:
        key = q["question"].strip().lower()[:100]
        if key not in seen:
            seen.add(key)
            unique.append(q)
    return unique


def _find_section_by_number(qtext: str, sections: list) -> tuple:
    """Find source section by extracting question number from AI output."""
    m = re.match(r"^\s*(\d+)\s*[.)]\s*", qtext)
    if m:
        num = m.group(1)
        for i, sec in enumerate(sections):
            sm = re.match(r"^##\s*(\d+)\.\s*", sec.strip())
            if sm and sm.group(1) == num:
                return i, sec
    return -1, None


def _recover_missing_content(validated: List[dict], original_text: str) -> int:
    """Post-processing: recover missing options/answers from source text for questions where AI failed.

    Scans original text for `- ` option lines and `**Answer:**` to patch
    questions with 0 options or missing correct_answers.
    Returns count of questions patched.
    """
    sections = re.split(r"(?=^## \d+\.)", original_text, flags=re.MULTILINE)
    if not sections:
        sections = [original_text]
    logger.info(f"[RECOVERY] Starting recovery: {len(validated)} questions, {len(sections)} sections")
    patched = 0

    for vq in validated:
        needs_options = not vq["options"] or len(vq["options"]) < 2
        needs_answers = not vq["correct_answers"]
        if not needs_options and not needs_answers:
            continue

        qtext = vq["question"].strip()
        qtext_lower = qtext.lower()[:100]

        best_sec = None
        best_idx = -1

        # Method 1: Match by question number (e.g., "## 10." for "10. Text")
        sec_idx, sec = _find_section_by_number(qtext, sections)
        if sec is not None:
            best_sec = sec
            best_idx = sec_idx
            logger.info(f"[RECOVERY] Matched by question number -> section {best_idx}")

        # Method 2: Fall back to word overlap matching
        if best_sec is None:
            qtext_clean = re.sub(r"^\d+\.\s*", "", qtext_lower)
            q_words = set(qtext_clean.split())
            logger.info(f"[RECOVERY] Number match failed, trying word overlap: {len(q_words)} words")
            best_score = 0
            for idx, sec in enumerate(sections):
                sec_clean = re.sub(r"^## \d+\.\s*", "", sec.strip().lower())[:100]
                score = len(q_words & set(sec_clean.split()))
                if score > best_score:
                    best_score = score
                    best_sec = sec
                    best_idx = idx

            if best_sec is None or best_score < 2:
                logger.info(f"[RECOVERY] No match for Q: {qtext_lower[:40]}... (best_score={best_score}, threshold=2)")
                continue
            logger.info(f"[RECOVERY] Matched word overlap -> section {best_idx} (score={best_score})")

        modified = False

        # 1. Recover options from `- ` bullet lines
        if needs_options:
            opt_lines = re.findall(r"^-\s+(.*)", best_sec, re.MULTILINE)
            logger.info(f"[RECOVERY] Found {len(opt_lines)} bullet lines in section {best_idx}")
            if opt_lines:
                clean_opts = []
                for o in opt_lines:
                    o = o.strip()
                    if o and o != "-":
                        if o not in clean_opts:
                            clean_opts.append(o)
                logger.info(f"[RECOVERY] Cleaned to {len(clean_opts)} options after filtering")
                if len(clean_opts) >= 2:
                    vq["options"] = clean_opts
                    if vq.get("type") in (None, "", "unknown"):
                        vq["type"] = "single"
                    modified = True
                    logger.info(f"[RECOVERY] Patched options for Q: {vq['question'][:50]}... ({len(clean_opts)} options)")

        # 2. If still needs options, try matching JSON items from answer
        if needs_options and (not vq["options"] or len(vq["options"]) < 2):
            match_items = _extract_matching_items_from_source(best_sec)
            if match_items:
                vq["options"] = match_items
                vq["type"] = "matching"
                modified = True
                logger.info(f"[RECOVERY] Patched matching options for Q: {vq['question'][:50]}... ({len(match_items)} items)")

        # 3. If still needs options, try fill-in-blank split from answer text
        if needs_options and (not vq["options"] or len(vq["options"]) < 2):
            ans_text = _extract_answer_from_section(best_sec)
            if ans_text:
                fib_opts = _extract_fill_in_blank_options(ans_text)
                if fib_opts:
                    vq["options"] = fib_opts
                    modified = True
                    logger.info(f"[RECOVERY] Patched fill-in-blank options for Q: {vq['question'][:50]}... ({len(fib_opts)} opts from answer)")

        # 4. Recover correct_answers from **Answer:**
        if needs_answers or (vq.get("options") and not vq["correct_answers"]):
            answer_text = _extract_answer_from_section(best_sec)
            logger.info(f"[RECOVERY] Answer recovery: found={answer_text is not None} for Q: {vq['question'][:40]}...")
            if answer_text:
                opts = vq.get("options", [])
                matched = False
                if opts:
                    for opt in opts:
                        opt_clean = re.sub(r"^[A-Za-z][)\s.]+\s*", "", opt).strip().lower()
                        ans_lower = answer_text.strip().lower()
                        if ans_lower == opt_clean or ans_lower in opt_clean or opt_clean in ans_lower:
                            vq["correct_answers"] = [opt]
                            matched = True
                            break
                if not matched:
                    vq["correct_answers"] = [answer_text]
                modified = True
                logger.info(f"[RECOVERY] Patched answer for Q: {vq['question'][:50]}... -> '{answer_text[:40]}' (matched={matched})")

        if modified:
            patched += 1

    logger.info(f"[RECOVERY] Done: patched {patched}/{len(validated)} questions")
    return patched


def _extract_answer_from_section(sec: str) -> Optional[str]:
    """Extract answer text from a source section. Handles plain text and embedded JSON."""
    answer_match = re.search(
        r"\*\*Answer:\*\*\s*(.*?)(?:\n_(?:Page|Seite)|$)",
        sec, re.IGNORECASE | re.DOTALL
    )
    if not answer_match:
        return None

    answer_text = answer_match.group(1).strip()
    # Remove trailing instructions like "Bitte ordnen Sie zu" or "Beurteile..."
    answer_text = re.sub(r"\s*[BW]itte\s.*$", "", answer_text).strip()
    answer_text = re.sub(r"\s*Beurteile\s.*$", "", answer_text).strip()

    # Check for JSON-like matching structure: {"groupName": "...", "items": [...]}
    if answer_text.startswith("{"):
        try:
            # Try to find and parse JSON objects in the answer
            items = []
            for m in re.finditer(r'"text"\s*:\s*"([^"]+)"', answer_text):
                items.append(m.group(1))
            if items:
                return "; ".join(items)
        except Exception:
            pass

    return answer_text


def _extract_matching_items_from_source(sec: str) -> Optional[list]:
    """Extract matching items from JSON embedded in answer line (e.g., 'Ordnen Sie zu' questions)."""
    am = re.search(
        r"\*\*Answer:\*\*\s*(.*?)(?:\n_(?:Page|Seite)|$)",
        sec, re.IGNORECASE | re.DOTALL
    )
    if not am:
        return None
    answer_text = am.group(1).strip()
    if not answer_text.startswith("{"):
        return None
    items = []
    for m in re.finditer(r'"text"\s*:\s*"([^"]+)"', answer_text):
        text = m.group(1).strip()
        if text and text not in items:
            items.append(text)
    if len(items) >= 2:
        return items
    # Fallback: extract from question text before answer
    q_lines = sec.split("\n")
    qtext = q_lines[0] if q_lines else ""
    parts = re.split(r"\s+(richtig|falsch)\s+", qtext, flags=re.IGNORECASE)
    items = [p.strip() for p in parts if p.strip() and len(p.strip()) > 5]
    return items if len(items) >= 2 else None


def _extract_fill_in_blank_options(answer_text: str) -> Optional[list]:
    """For fill-in-blank questions, create options from the answer text split by delimiters."""
    for delim in [" ", ",", ";", " und ", " bzw. ", " / "]:
        parts = [p.strip() for p in answer_text.split(delim) if p.strip()]
        if len(parts) >= 2:
            return parts
    return None


def _clean_duplicate_options(validated: List[dict]) -> int:
    """Remove duplicate options from questions. Returns count of cleaned questions."""
    cleaned = 0
    for vq in validated:
        opts = vq.get("options", [])
        if not opts:
            continue
        seen = set()
        unique_opts = []
        for o in opts:
            key = o.strip().lower()
            if key not in seen:
                seen.add(key)
                unique_opts.append(o)
        if len(unique_opts) < len(opts):
            vq["options"] = unique_opts
            cleaned += 1
            logger.info(f"[CLEAN] Removed {len(opts) - len(unique_opts)} dupes from Q: {vq['question'][:40]}...")
    return cleaned


async def extract_questions_from_text(
    text: str,
    source_file: str = "",
) -> List[ParsedQuestion]:
    """Main entry point: chunk document, extract via AI, validate, return ParsedQuestions."""
    if not text or not text.strip():
        logger.warning("[AI_EXTRACTOR] Empty input text")
        return []

    chunks = chunk_document(text)
    logger.info(f"[AI_EXTRACTOR] Split document into {len(chunks)} chunks")

    all_raw = []
    for i, chunk in enumerate(chunks):
        extracted = await extract_questions_from_chunk(chunk, i)
        all_raw.extend(extracted)
        logger.info(f"[AI_EXTRACTOR] Chunk {i}: extracted {len(extracted)} raw questions")

    # Validate each with detailed categorization
    validated = []
    skipped = 0
    malformed_count = 0
    merged_count = 0
    missing_answers = 0
    missing_options = 0

    for i, q in enumerate(all_raw):
        # Merge detection on raw question text
        raw_text = (q.get("question") or q.get("question_text") or "").strip()
        if raw_text:
            mi = _detect_merge_indicators(raw_text)
            if mi:
                merged_count += 1

        vq = validate_extracted_question(q, i)
        if vq:
            validated.append(vq)
            if not vq["correct_answers"]:
                missing_answers += 1
            if not vq["options"] or len(vq["options"]) < 2:
                missing_options += 1
        else:
            skipped += 1
            malformed_count += 1

    # Deduplicate
    validated = _deduplicate_questions(validated)

    # Recovery pass: patch questions where AI missed options or answers
    recovered = _recover_missing_content(validated, text)
    logger.info(f"[AI_EXTRACTOR] Recovery result: patched={recovered} total={len(validated)}")
    # Detailed verification log for questions that still need help
    needs_help = sum(1 for v in validated if not v["options"] or len(v["options"]) < 2 or not v["correct_answers"])
    logger.info(f"[AI_EXTRACTOR] Post-recovery needs help: {needs_help} of {len(validated)} questions")
    for i, vq in enumerate(validated):
        no_opts = not vq["options"] or len(vq["options"]) < 2
        no_ans = not vq["correct_answers"]
        if no_opts or no_ans:
            logger.info(f"[AI_EXTRACTOR] Post-recovery Q{i} still broken: opts={len(vq['options'])} ans={len(vq['correct_answers'])} q={vq['question'][:60]}")

    # Clean duplicate options
    cleaned = _clean_duplicate_options(validated)
    if cleaned:
        logger.info(f"[AI_EXTRACTOR] Cleaned duplicate options from {cleaned} questions")

    logger.info(
        f"[AI_EXTRACTOR] Stats: {len(all_raw)} raw → {len(validated)} valid "
        f"({malformed_count} malformed, {merged_count} merged-like, "
        f"{missing_answers} missing answers, {missing_options} missing options, "
        f"{recovered} recovered)"
    )
    if skipped:
        logger.warning(f"[AI_EXTRACTOR] Skipped {skipped} malformed questions")

    # Convert to ParsedQuestion
    result = []
    for i, vq in enumerate(validated):
        result.append(ParsedQuestion(
            question=vq["question"],
            type=vq.get("type", "single"),
            options=vq["options"],
            correct_answers=vq["correct_answers"],
            source_file=source_file,
            status="parsed",
        ))

    logger.info(f"[AI_EXTRACTOR] Final: {len(result)} valid questions from {len(chunks)} chunks")
    return result


async def extract_and_report(text: str, source_file: str = "") -> dict:
    """Extract questions with detailed reporting. Returns both questions and report."""
    chunks = chunk_document(text)
    report = {
        "source_file": source_file,
        "total_chunks": len(chunks),
        "total_raw_from_ai": 0,
        "validated": 0,
        "skipped": 0,
        "deduplicated": 0,
        "final_count": 0,
        # Detailed stats
        "malformed_questions": 0,
        "merged_questions_detected": 0,
        "missing_answers": 0,
        "missing_options": 0,
        "malformed_details": [],
        "questions": [],
        "chunk_details": [],
        "stats": {
            "by_type": {},
            "answers_with_options": 0,
            "options_ok": 0,
        },
    }

    all_raw = []
    for i, chunk in enumerate(chunks):
        extracted = await extract_questions_from_chunk(chunk, i)
        all_raw.extend(extracted)
        report["chunk_details"].append({"chunk": i, "extracted": len(extracted)})

    report["total_raw_from_ai"] = len(all_raw)

    validated = []
    skipped = 0
    malformed = 0
    merged_count = 0
    missing_ans = 0
    missing_opts = 0
    malformed_details = []
    by_type = {}
    answers_with_opts = 0
    opts_ok = 0

    for i, q in enumerate(all_raw):
        raw_text = (q.get("question") or q.get("question_text") or "").strip()
        merge_indicators = _detect_merge_indicators(raw_text) if raw_text else []
        if merge_indicators:
            merged_count += 1

        vq = validate_extracted_question(q, i)
        if vq:
            validated.append(vq)
            # Per-type stats
            t = vq["type"]
            by_type[t] = by_type.get(t, 0) + 1
            if vq["correct_answers"]:
                answers_with_opts += 1
            else:
                missing_ans += 1
            if vq["options"] and len(vq["options"]) >= 2:
                opts_ok += 1
            else:
                missing_opts += 1
        else:
            skipped += 1
            malformed += 1
            # Classify why
            if not raw_text:
                reason = "empty_question_text"
            elif not isinstance(q, dict):
                reason = "not_a_dict"
            else:
                reason = "validation_failed"
            malformed_details.append({"index": i, "reason": reason, "preview": raw_text[:80]})

    report["validated"] = len(validated)
    report["skipped"] = skipped
    report["malformed_questions"] = malformed
    report["merged_questions_detected"] = merged_count
    report["missing_answers"] = missing_ans
    report["missing_options"] = missing_opts
    report["malformed_details"] = malformed_details
    report["stats"]["by_type"] = by_type
    report["stats"]["answers_with_options"] = answers_with_opts
    report["stats"]["options_ok"] = opts_ok

    before_dedup = len(validated)
    validated = _deduplicate_questions(validated)
    report["deduplicated"] = before_dedup - len(validated)

    # Recovery pass
    recovered = _recover_missing_content(validated, text)
    report["recovered"] = recovered
    if recovered:
        logger.info(f"[AI_EXTRACTOR] Report recovery: patched {recovered} questions")

    # Clean duplicate options
    cleaned = _clean_duplicate_options(validated)
    report["cleaned_duplicates"] = cleaned
    if cleaned:
        logger.info(f"[AI_EXTRACTOR] Cleaned duplicate options from {cleaned} questions")

    report["final_count"] = len(validated)
    report["questions"] = validated

    logger.info(
        f"[AI_EXTRACTOR] Report: {len(all_raw)} raw → {len(validated)} validated "
        f"({malformed} malformed, {merged_count} merged-like, "
        f"{missing_ans} missing answers, {missing_opts} missing options) "
        f"→ {report['final_count']} final after dedup"
    )

    return report
