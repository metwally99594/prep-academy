"""
Temporary: returns zero vectors — no local ONNX model loaded.
Embedding will be restored via OpenRouter/OpenAI API in the next deploy.
"""
import logging
logger = logging.getLogger(__name__)

VECTOR_DIM = 384


def embed_text(text: str) -> list[float]:
    """Return zero vector. Qdrant searches return nothing → regex fallback."""
    if not text or not text.strip():
        return [0.0] * VECTOR_DIM
    return [0.0] * VECTOR_DIM


def embed_query(query: str) -> list[float]:
    """Return zero vector. Qdrant searches return nothing → regex fallback."""
    if not query or not query.strip():
        return [0.0] * VECTOR_DIM
    return [0.0] * VECTOR_DIM
