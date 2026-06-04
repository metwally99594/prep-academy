"""Question parser — extracts structured questions from raw text (PDF/Markdown output).

Supports formats:
  ## Question
  What is ...?
  A) Option 1
  B) Option 2
  Answer: Option 1
  Answer: A
  Correct answers: A, C
"""
import re as _re
from typing import List
from models import ParsedQuestion


def parse_questions_from_text(text: str, source_file: str = "") -> List[ParsedQuestion]:
    """Parse a block of text and extract all questions found."""
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
    blocks = _re.split(combined, text, flags=_re.MULTILINE | _re.IGNORECASE)
    # Each non-empty block is a question; the separator itself is consumed
    result = [b.strip() for b in blocks if b and b.strip()]
    if not result and text.strip():
        result = [text.strip()]
    return result


def _parse_single_question(block: str, source_file: str) -> ParsedQuestion:
    """Parse a single question block into a ParsedQuestion."""
    lines = block.strip().split("\n")
    question_lines = []
    options = []
    correct_answers_raw = []
    in_options = False

    # Patterns
    option_pattern = _re.compile(r'^\s*([A-Za-z])[.)]\s+(.*)')
    answer_pattern = _re.compile(
        r'(?:Correct\s*)?(?:Answer|Antwort)(?:\s*:|s?\s*:)?\s*(.*)',
        _re.IGNORECASE
    )

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for answer line
        answer_match = answer_pattern.match(stripped)
        if answer_match:
            raw = answer_match.group(1).strip()
            correct_answers_raw = [a.strip() for a in raw.replace(" and ", ",").replace(" und ", ",").split(",")]
            continue

        # Check for option line
        opt_match = option_pattern.match(stripped)
        if opt_match:
            options.append(stripped)
            in_options = True
            continue

        # If not in options yet, treat as question text
        if not in_options:
            question_lines.append(stripped)

    question_text = " ".join(question_lines).strip()
    # Remove leading "Question" or "Frage" header remnants
    question_text = _re.sub(r'^(Question|Frage)\s*[:\-]?\s*', '', question_text, flags=_re.IGNORECASE).strip()

    # Resolve correct answers — could be option letters or full text
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

    # Build lookup: letter -> full option text, and full text (lower) -> full option text
    letter_map = {}
    text_map = {}
    for opt in options:
        m = _re.match(r'^\s*([A-Za-z])[.)]\s+(.*)', opt)
        if m:
            letter = m.group(1).upper()
            text = m.group(2).strip()
            letter_map[letter] = opt.strip()
            text_map[text.lower()] = opt.strip()

    for ans in raw_answers:
        ans = ans.strip()
        ans_upper = ans.upper()
        ans_lower = ans.lower()
        # Split by comma or semicolon (support "A, C" or "A; C")
        for part in _re.split(r'[,;]\s*', ans_upper):
            part = part.strip()
            if part in letter_map:
                resolved.append(letter_map[part])
            elif ans_lower in text_map:
                resolved.append(text_map[ans_lower])
                break  # matched full text, don't split further
            else:
                # Try matching the original (un-uppercased) part against option text
                original_part = ans
                if original_part.lower() in text_map:
                    resolved.append(text_map[original_part.lower()])
                elif part and not part.isspace():
                    resolved.append(part)

    return resolved
