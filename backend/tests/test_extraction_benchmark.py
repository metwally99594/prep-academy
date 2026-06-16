import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation import extraction_benchmark as bench


def test_compare_records_reports_complete_accuracy():
    expected = [
        bench.QuestionRecord(
            index=0,
            question="What is first-line therapy for pneumonia?",
            options=["Antibiotics", "Observation"],
            correct_answers=["Antibiotics"],
            raw={},
        )
    ]
    actual = [
        bench.QuestionRecord(
            index=0,
            question="What is the first-line therapy for pneumonia?",
            options=["Antibiotics", "Observation", "Surgery"],
            correct_answers=["Antibiotics"],
            raw={},
        )
    ]

    report = bench.compare_records(expected, actual, threshold=0.6)

    assert report["summary"]["question_recall_pct"] == 100.0
    assert report["summary"]["options_accuracy_pct"] == 100.0
    assert report["summary"]["answers_accuracy_pct"] == 100.0
    assert report["summary"]["complete_accuracy_pct"] == 100.0
    assert report["summary"]["target_met"] is True


def test_compare_records_classifies_missing_question():
    expected = [
        bench.QuestionRecord(0, "A unique cardiology question", ["A", "B"], ["A"], {}),
    ]
    actual = [
        bench.QuestionRecord(0, "Unrelated dermatology prompt", ["X", "Y"], ["X"], {}),
    ]

    report = bench.compare_records(expected, actual, threshold=0.9)

    assert report["summary"]["complete_accuracy_pct"] == 0.0
    assert report["failures"][0]["issues"] == ["question_not_found"]
