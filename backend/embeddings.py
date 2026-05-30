"""
OpenRouter/OpenAI embeddings via text-embedding-3-small (384d).
Async API calls — zero local RAM usage.
"""
import logging, os, asyncio, time, random
from collections import OrderedDict

logger = logging.getLogger(__name__)

VECTOR_DIM = 384
_OR_URL = "https://openrouter.ai/api/v1/embeddings"
_MODEL = "openai/text-embedding-3-small"
_MAX_RETRIES = 5
_RETRY_BASE = 1.0  # seconds, doubled per attempt with jitter

# In-memory LRU cache for embed_query (repeated tutor queries)
_query_cache = OrderedDict()
_CACHE_MAX = 200
_CACHE_TTL = 900  # 15 seconds


async def _call_api(texts: list[str], dims: int = VECTOR_DIM) -> list[list[float]] | None:
    """Call OpenRouter embeddings with exponential backoff + jitter. Returns vectors or None."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        logger.warning("[EMBED] OPENROUTER_API_KEY not set")
        return None

    import httpx
    for attempt in range(_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=60.0) as cl:
                resp = await cl.post(
                    _OR_URL,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": _MODEL, "input": texts, "dimensions": dims},
                )
            if resp.status_code == 429:
                delay = _RETRY_BASE * (2 ** attempt) * (0.75 + random.random() * 0.5)
                logger.warning(f"[EMBED] 429 rate limit, retry {attempt+1}/{_MAX_RETRIES} in {delay:.1f}s")
                await asyncio.sleep(delay)
                continue
            resp.raise_for_status()
            data = resp.json()
            items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
            vectors = [item["embedding"] for item in items]
            logger.info(f"[EMBED] API returned {len(vectors)} vectors, dim={len(vectors[0]) if vectors else 0}")
            return vectors
        except httpx.HTTPStatusError as e:
            logger.warning(f"[EMBED] HTTP {e.response.status_code} (attempt {attempt+1}/{_MAX_RETRIES})")
        except Exception as e:
            logger.warning(f"[EMBED] API error: {e} (attempt {attempt+1}/{_MAX_RETRIES})")
        if attempt < _MAX_RETRIES - 1:
            delay = _RETRY_BASE * (2 ** attempt) * (0.75 + random.random() * 0.5)
            await asyncio.sleep(delay)
    logger.error(f"[EMBED] All {_MAX_RETRIES} attempts failed — returning None")
    return None


async def embed_text(text: str) -> list[float]:
    """Embed single text. Returns 384d vector or zero vector (regex fallback)."""
    if not text or not text.strip():
        return [0.0] * VECTOR_DIM
    vecs = await _call_api([text[:5000]])
    if vecs and len(vecs) == 1:
        return vecs[0]
    return [0.0] * VECTOR_DIM


async def embed_query(query: str) -> list[float]:
    """Embed single query with in-memory cache. Returns 384d vector or zero vector."""
    if not query or not query.strip():
        return [0.0] * VECTOR_DIM
    cache_key = query.strip()[:2000]
    now = time.time()
    # Check cache
    if cache_key in _query_cache:
        ts, vec = _query_cache[cache_key]
        if now - ts < _CACHE_TTL:
            logger.info(f"[EMBED] CACHE HIT for '{query[:60]}'")
            _query_cache.move_to_end(cache_key)
            return vec
        del _query_cache[cache_key]
    # Cache miss
    logger.info(f"[EMBED] CACHE MISS for '{query[:60]}'")
    vecs = await _call_api([cache_key])
    result = vecs[0] if vecs and len(vecs) == 1 else [0.0] * VECTOR_DIM
    _query_cache[cache_key] = (time.time(), result)
    if len(_query_cache) > _CACHE_MAX:
        _query_cache.popitem(last=False)
    return result


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed all texts in a single API call. Returns list of 384d vectors.
    On total failure, returns all-zero vectors for every input."""
    if not texts:
        return []
    truncated = [t[:5000] for t in texts]
    logger.info(f"[EMBED] embed_batch: sending {len(truncated)} texts")
    vecs = await _call_api(truncated)
    if vecs and len(vecs) == len(truncated):
        logger.info(f"[EMBED] embed_batch: received {len(vecs)} vectors")
        return vecs
    logger.warning(f"[EMBED] embed_batch: API returned {len(vecs) if vecs else 0}/{len(truncated)} — returning zero vectors")
    return [[0.0] * VECTOR_DIM for _ in texts]
