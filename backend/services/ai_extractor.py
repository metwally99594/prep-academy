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

    logger.info(
        f"[AI_EXTRACTOR] Stats: {len(all_raw)} raw → {len(validated)} valid "
        f"({malformed_count} malformed, {merged_count} merged-like, "
        f"{missing_answers} missing answers, {missing_options} missing options)"
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
    report["final_count"] = len(validated)
    report["questions"] = validated

    logger.info(
        f"[AI_EXTRACTOR] Report: {len(all_raw)} raw → {len(validated)} validated "
        f"({malformed} malformed, {merged_count} merged-like, "
        f"{missing_ans} missing answers, {missing_opts} missing options) "
        f"→ {report['final_count']} final after dedup"
    )

    return report
