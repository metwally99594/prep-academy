# Phase 3 Benchmark Workflow

Goal: measure AI question extraction against the 437-question gold file and iterate until complete accuracy is 95%+.

## Input format

Use JSON, JSONL, or CSV. Each row/object should include:

- `question`
- `options`
- `correct_answers`

Aliases are supported: `question_text`, `question_text_de`, `choices`, `choices_de`, `answer`, `correct_answer`.

## Run

First export the extraction result from the app or `/api/admin/question-import/extract-report`.

Then run:

```bash
python backend/evaluation/extraction_benchmark.py \
  --expected data/benchmark_437.json \
  --actual artifacts/extract_report.json \
  --out artifacts/extraction_benchmark_report.json
```

The script prints:

- question recall
- options accuracy
- answers accuracy
- complete accuracy
- failed cases with mismatch reasons

## Acceptance target

Phase 3 target is `complete_accuracy_pct >= 95.0`.

Use the failures list to classify issues into:

- `question_not_found`
- `options_mismatch`
- `answers_mismatch`

Fix parser/recovery/prompt behavior, rerun extraction, then rerun this benchmark until the target is met.
