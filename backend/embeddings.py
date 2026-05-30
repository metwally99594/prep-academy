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
        _embedder = TextEmbedding(
            model_name=MODEL_NAME,
            max_length=512,
        )
        logger.info(f"Embedding model loaded: {MODEL_NAME}")
    return _embedder

def embed_text(text: str) -> list[float]:
    if not text or not text.strip():
        return [0.0] * VECTOR_DIM
    model = _get_embedder()
    vec = list(model.embed([text[:5000]]))
    return vec[0].tolist() if vec else [0.0] * VECTOR_DIM

def embed_query(query: str) -> list[float]:
    if not query or not query.strip():
        return [0.0] * VECTOR_DIM
    model = _get_embedder()
    vec = list(model.embed([query[:2000]]))
    return vec[0].tolist() if vec else [0.0] * VECTOR_DIM
