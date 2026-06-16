import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation import obsidian_rag_benchmark as bench


def test_load_cases_accepts_aliases(tmp_path):
    cases_file = tmp_path / "cases.json"
    cases_file.write_text(
        json.dumps({
            "cases": [
                {"question": "diabetes criteria", "vault_path": "Endocrine/Diabetes.md"},
                {"query": "ignore missing expected"},
                {"q": "asthma treatment", "expected_note": "Resp/Asthma.md"},
            ]
        }),
        encoding="utf-8",
    )

    cases = bench._load_cases(cases_file)

    assert cases == [
        {"query": "diabetes criteria", "expected_path": "Endocrine/Diabetes.md"},
        {"query": "asthma treatment", "expected_path": "Resp/Asthma.md"},
    ]


def test_run_reports_recall_mrr_and_latency(monkeypatch):
    responses = {
        "diabetes": [
            {"vault_path": "Other.md"},
            {"vault_path": "Endocrine/Diabetes.md"},
        ],
        "asthma": [
            {"vault_path": "Resp/Asthma.md"},
        ],
    }

    def fake_search(base_url, token, query, limit):
        return responses[query], 25.0 if query == "diabetes" else 50.0

    monkeypatch.setattr(bench, "_search", fake_search)

    report = bench.run(
        [
            {"query": "diabetes", "expected_path": "Endocrine/Diabetes.md"},
            {"query": "asthma", "expected_path": "Resp/Asthma.md"},
        ],
        "https://example.test",
        "token",
    )

    assert report["summary"]["cases"] == 2
    assert report["summary"]["recall_at_5"] == 1.0
    assert report["summary"]["recall_at_10"] == 1.0
    assert report["summary"]["mrr"] == 0.75
    assert report["summary"]["avg_latency_ms"] == 37.5
    assert report["summary"]["p95_latency_ms"] == 50.0
