import logging
logger = logging.getLogger(__name__)

_embedder = None

def _get_embedder():
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding
        _embedder = TextEmbedding(
            model_name="intfloat/multilingual-e5-small",
            max_length=512,
        )
        logger.info("Embedding model loaded: intfloat/multilingual-e5-small")
    return _embedder

def embed_text(text: str) -> list[float]:
    if not text or not text.strip():
        return [0.0] * 384
    model = _get_embedder()
    vec = list(model.embed(["passage: " + text[:5000]]))
    return vec[0].tolist()

def embed_query(query: str) -> list[float]:
    if not query or not query.strip():
        return [0.0] * 384
    model = _get_embedder()
    vec = list(model.query_embed([query[:2000]]))
    return vec[0].tolist()
