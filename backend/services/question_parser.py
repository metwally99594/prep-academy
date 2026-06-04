"""Question parser — extracts structured questions from exam document text.

Primary method: AI-powered extraction via DeepSeek (services/ai_extractor).
Fallback method: regex-based parsing for simple structured formats.

Supports question types:
  - single choice
  - multiple choice
  - true/false
  - matching
  - grouping
  - image-based
"""
import re, json, asyncio
from typing import List, Optional, Tuple
from models import ParsedQuestion
from services.ai_extractor import extract_questions_from_text, extract_and_report


async def parse_questions_from_text_async(
    text: str, source_file: str = ""
) -> List[ParsedQuestion]:
    """Primary entry point. Uses AI extraction, falls back to regex on empty result."""
    ai_result = await extract_questions_from_text(text, source_file=source_file)
    if ai_result:
        return ai_result

    # Fallback: regex parser
    legacy = parse_questions_from_text(text, source_file=source_file)
    if legacy:
        return legacy

    return []


def parse_questions_from_text(text: str, source_file: str = "") -> List[ParsedQuestion]:
    """Legacy regex-based parser fallback."""
    questions: List[ParsedQuestion] = []
    blocks = _split_question_blocks(text)

    for block in blocks:
        q = _parse_single_question(block, source_file)
        if q and q.question.strip():
            questions.append(q)

    return questions


def _split_question_blocks(text: str) -> List[str]:
    """Split text into individual question blocks."""
    separators = [
        r'^##\s*(?:Question|Frage)\b',
        r'^\d+[.)]\s+(?=[A-ZÄÖÜ])',
    ]
    combined = "|".join(f"(?:{s})" for s in separators)
    blocks = re.split(combined, text, flags=re.MULTILINE | re.IGNORECASE)
    result = [b.strip() for b in blocks if b and b.strip()]
    if not result and text.strip():
        result = [text.strip()]
    return result


def _parse_single_question(block: str, source_file: str) -> ParsedQuestion:
    """Legacy regex-based single question parser."""
    lines = block.strip().split("\n")
    question_lines = []
    options = []
    correct_answers_raw = []
    in_options = False

    option_pattern = re.compile(r'^\s*([A-Za-z])[.)]\s+(.*)')
    answer_pattern = re.compile(
        r'(?:Correct\s*)?(?:Answer|Antwort)(?:\s*:|s?\s*:)?\s*(.*)',
        re.IGNORECASE
    )

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        answer_match = answer_pattern.match(stripped)
        if answer_match:
            raw = answer_match.group(1).strip()
            correct_answers_raw = [a.strip() for a in raw.replace(" and ", ",").replace(" und ", ",").split(",")]
            continue

        opt_match = option_pattern.match(stripped)
        if opt_match:
            options.append(stripped)
            in_options = True
            continue

        if not in_options:
            question_lines.append(stripped)

    question_text = " ".join(question_lines).strip()
    question_text = re.sub(r'^(Question|Frage)\s*[:\-]?\s*', '', question_text, flags=re.IGNORECASE).strip()
    correct_answers = _resolve_correct_answers(correct_answers_raw, options)

    return ParsedQuestion(
        question=question_text,
        options=options,
        correct_answers=correct_answers,
        source_file=source_file,
        status="parsed"
    )


def _resolve_correct_answers(raw_answers: List[str], options: List[str]) -> List[str]:
    """Convert answer references (letters or text) to the canonical option strings."""
    resolved = []
    letter_map = {}
    text_map = {}
    for opt in options:
        m = re.match(r'^\s*([A-Za-z])[.)]\s+(.*)', opt)
        if m:
            letter = m.group(1).upper()
            text = m.group(2).strip()
            letter_map[letter] = opt.strip()
            text_map[text.lower()] = opt.strip()

    for ans in raw_answers:
        ans = ans.strip()
        ans_upper = ans.upper()
        ans_lower = ans.lower()
        for part in re.split(r'[,;]\s*', ans_upper):
            part = part.strip()
            if part in letter_map:
                resolved.append(letter_map[part])
            elif ans_lower in text_map:
                resolved.append(text_map[ans_lower])
                break
            else:
                original_part = ans
                if original_part.lower() in text_map:
                    resolved.append(text_map[original_part.lower()])
                elif part and not part.isspace():
                    resolved.append(part)

    return resolved


async def extract_with_report(text: str, source_file: str = "") -> dict:
    """Run AI extraction with detailed reporting. For diagnostics and accuracy measurement."""
    return await extract_and_report(text, source_file=source_file)
