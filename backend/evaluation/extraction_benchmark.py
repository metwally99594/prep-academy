"""Question extraction benchmark runner.

Compares a gold/expected question file against an extracted output file.

Supported inputs:
- JSON list of question objects
- JSON object with a "questions" list
- JSONL, one object per line
- CSV with columns such as question, options, correct_answers

Example:
    python backend/evaluation/extraction_benchmark.py \
        --expected data/benchmark_437.json \
        --actual artifacts/extract_report.json \
        --out artifacts/extraction_benchmark_report.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


QUESTION_KEYS = ("question", "question_text", "question_text_de", "stem")
OPTION_KEYS = ("options", "choices", "choices_de", "final_options")
ANSWER_KEYS = ("correct_answers", "answers", "answer", "correct", "correct_answer")


@dataclass
class QuestionRecord:
    index: int
    question: str
    options: list[str]
    correct_answers: list[str]
    raw: dict[str, Any]


@dataclass
class MatchResult:
    expected_index: int
    actual_index: int | None
    similarity: float
    question_ok: bool
    options_ok: bool
    answers_ok: bool
    complete_ok: bool
    expected_question: str
    actual_question: str | None
    issues: list[str]


def _first_value(item: dict[str, Any], keys: tuple[str, ...], default: Any = "") -> Any:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return default


def _split_listish(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        result = []
        for entry in value:
            if isinstance(entry, dict):
                text = entry.get("text") or entry.get("label") or entry.get("value") or str(entry)
            else:
                text = str(entry)
            text = text.strip()
            if text:
                result.append(text)
        return result
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return _split_listish(parsed)
        except json.JSONDecodeError:
            pass
        return [p.strip() for p in re.split(r"\s*(?:\||;)\s*", stripped) if p.strip()]
    return [str(value).strip()]


def _normalize_text(text: str) -> str:
    text = re.sub(r"^[A-Za-z0-9]+[.)]\s*", "", text or "")
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]+", "", text, flags=re.UNICODE)
    return text.strip()


def _token_similarity(a: str, b: str) -> float:
    a_norm = _normalize_text(a)
    b_norm = _normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 1.0
    a_tokens = set(a_norm.split())
    b_tokens = set(b_norm.split())
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


def _normalize_list(values: list[str]) -> set[str]:
    return {_normalize_text(v) for v in values if _normalize_text(v)}


def _coerce_record(item: dict[str, Any], index: int) -> QuestionRecord:
    question = str(_first_value(item, QUESTION_KEYS, "")).strip()
    options = _split_listish(_first_value(item, OPTION_KEYS, []))
    answers = _split_listish(_first_value(item, ANSWER_KEYS, []))
    return QuestionRecord(
        index=index,
        question=question,
        options=options,
        correct_answers=answers,
        raw=item,
    )


def load_records(path: Path) -> list[QuestionRecord]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        return [_coerce_record(dict(row), i) for i, row in enumerate(rows)]

    text = path.read_text(encoding="utf-8-sig")
    if suffix == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        data = json.loads(text)
        if isinstance(data, dict):
            rows = data.get("questions") or data.get("items") or data.get("data") or []
        else:
            rows = data

    if not isinstance(rows, list):
        raise ValueError(f"{path} does not contain a question list")
    return [_coerce_record(dict(row), i) for i, row in enumerate(rows)]


def _find_best_match(
    expected: QuestionRecord,
    actual: list[QuestionRecord],
    used_actual: set[int],
) -> tuple[QuestionRecord | None, float]:
    best = None
    best_score = 0.0
    for candidate in actual:
        if candidate.index in used_actual:
            continue
        score = _token_similarity(expected.question, candidate.question)
        if score > best_score:
            best = candidate
            best_score = score
    return best, best_score


def compare_records(
    expected: list[QuestionRecord],
    actual: list[QuestionRecord],
    threshold: float = 0.72,
) -> dict[str, Any]:
    used_actual: set[int] = set()
    matches: list[MatchResult] = []

    for exp in expected:
        act, similarity = _find_best_match(exp, actual, used_actual)
        issues = []
        question_ok = bool(act and similarity >= threshold)
        options_ok = False
        answers_ok = False

        if act and question_ok:
            used_actual.add(act.index)
            exp_opts = _normalize_list(exp.options)
            act_opts = _normalize_list(act.options)
            exp_ans = _normalize_list(exp.correct_answers)
            act_ans = _normalize_list(act.correct_answers)

            options_ok = bool(exp_opts) and exp_opts.issubset(act_opts)
            answers_ok = bool(exp_ans) and exp_ans.issubset(act_ans | act_opts)

            if not options_ok:
                issues.append("options_mismatch")
            if not answers_ok:
                issues.append("answers_mismatch")
        else:
            issues.append("question_not_found")

        matches.append(MatchResult(
            expected_index=exp.index,
            actual_index=act.index if act and question_ok else None,
            similarity=round(similarity, 4),
            question_ok=question_ok,
            options_ok=options_ok,
            answers_ok=answers_ok,
            complete_ok=question_ok and options_ok and answers_ok,
            expected_question=exp.question,
            actual_question=act.question if act and question_ok else None,
            issues=issues,
        ))

    total = len(expected)
    found = sum(1 for m in matches if m.question_ok)
    options_ok = sum(1 for m in matches if m.options_ok)
    answers_ok = sum(1 for m in matches if m.answers_ok)
    complete_ok = sum(1 for m in matches if m.complete_ok)
    extra_actual = max(0, len(actual) - len(used_actual))

    def pct(n: int) -> float:
        return round((n / total * 100) if total else 0.0, 2)

    return {
        "summary": {
            "expected_total": total,
            "actual_total": len(actual),
            "matched_questions": found,
            "extra_actual": extra_actual,
            "question_recall_pct": pct(found),
            "options_accuracy_pct": pct(options_ok),
            "answers_accuracy_pct": pct(answers_ok),
            "complete_accuracy_pct": pct(complete_ok),
            "target_pct": 95.0,
            "target_met": pct(complete_ok) >= 95.0,
        },
        "failures": [asdict(m) for m in matches if not m.complete_ok],
        "matches": [asdict(m) for m in matches],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark question extraction accuracy.")
    parser.add_argument("--expected", required=True, type=Path, help="Gold benchmark file")
    parser.add_argument("--actual", required=True, type=Path, help="Extractor output/report file")
    parser.add_argument("--out", type=Path, help="Optional JSON report output path")
    parser.add_argument("--threshold", type=float, default=0.72, help="Question match similarity threshold")
    args = parser.parse_args()

    expected = load_records(args.expected)
    actual = load_records(args.actual)
    report = compare_records(expected, actual, threshold=args.threshold)

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved full report to {args.out}")

    return 0 if report["summary"]["target_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
