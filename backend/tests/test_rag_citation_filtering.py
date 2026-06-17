import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.rag import _filter_relevant_sources


def test_filter_relevant_sources_drops_low_relevance_tail():
    sources = [
        {"index": 1, "source": "strong", "retrieval_score": 0.93},
        {"index": 2, "source": "borderline", "retrieval_score": 0.75},
        {"index": 3, "source": "weak", "retrieval_score": 0.42},
    ]

    filtered, removed = _filter_relevant_sources(sources, threshold=0.75)

    assert removed == 1
    assert [s["source"] for s in filtered] == ["strong", "borderline"]
    assert [s["index"] for s in filtered] == [1, 2]


def test_filter_relevant_sources_keeps_best_fallback_when_all_scores_are_low():
    sources = [
        {"index": 1, "source": "weak-a", "retrieval_score": 0.22},
        {"index": 2, "source": "weak-b", "retrieval_score": 0.48},
    ]

    filtered, removed = _filter_relevant_sources(sources, threshold=0.75)

    assert removed == 1
    assert filtered == [{"index": 1, "source": "weak-b", "retrieval_score": 0.48}]


def test_filter_relevant_sources_uses_normalized_score_when_retrieval_score_missing():
    sources = [
        {"index": 1, "source": "normalized", "score": 0.8},
        {"index": 2, "source": "raw-rerank", "score": 2.7, "vector_score": 0.2},
    ]

    filtered, removed = _filter_relevant_sources(sources, threshold=0.75)

    assert removed == 1
    assert filtered[0]["source"] == "normalized"
