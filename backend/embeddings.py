import logging, warnings
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", message=".*now uses mean pooling.*")

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
VECTOR_DIM = 384

_embedder = None

def _get_embedder():
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding
        logger.info(f"[EMBED] Creating TextEmbedding(model_name='{MODEL_NAME}', max_length=512)...")
        _embedder = TextEmbedding(
            model_name=MODEL_NAME,
            max_length=512,
        )
        logger.info(f"[EMBED] TextEmbedding created successfully: {MODEL_NAME}")
    return _embedder

def embed_text(text: str) -> list[float]:
    if not text or not text.strip():
        logger.warning("[EMBED] embed_text called with empty text")
        return [0.0] * VECTOR_DIM
    text_len = min(len(text), 5000)
    logger.info(f"[EMBED] embed_text: getting embedder (text length={text_len})")
    model = _get_embedder()
    logger.info(f"[EMBED] embed_text: calling model.embed() on text[:{text_len}]...")
    vec = list(model.embed([text[:5000]]))
    if vec:
        v = vec[0].tolist()
        logger.info(f"[EMBED] embed_text: returned vector len={len(v)}, first_5={v[:5]}")
        return v
    else:
        logger.warning("[EMBED] embed_text: model.embed() returned empty list")
        return [0.0] * VECTOR_DIM

def embed_query(query: str) -> list[float]:
    if not query or not query.strip():
        logger.warning("[EMBED] embed_query called with empty query")
        return [0.0] * VECTOR_DIM
    qlen = min(len(query), 2000)
    logger.info(f"[EMBED] embed_query: getting embedder (query length={qlen})")
    model = _get_embedder()
    logger.info(f"[EMBED] embed_query: calling model.embed() on query[:{qlen}]...")
    vec = list(model.embed([query[:2000]]))
    if vec:
        v = vec[0].tolist()
        logger.info(f"[EMBED] embed_query: returned vector len={len(v)}, first_5={v[:5]}")
        return v
    else:
        logger.warning("[EMBED] embed_query: model.embed() returned empty list")
        return [0.0] * VECTOR_DIM
