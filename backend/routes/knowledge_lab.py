"""Knowledge Lab — admin-only wiki browser."""

from fastapi import APIRouter, HTTPException, Depends, Query
from auth import get_admin_user
from services.knowledge_lab_service import (
    discover_pages,
    get_page,
    search,
    build_index,
    get_stats,
)

router = APIRouter(prefix="/api/knowledge-lab", tags=["knowledge-lab"])


@router.get("/pages")
async def list_pages(user: dict = Depends(get_admin_user)):
    """List all wiki pages with metadata."""
    pages = discover_pages()
    return {"pages": pages, "total": len(pages)}


@router.get("/pages/{path:path}")
async def read_page(path: str, user: dict = Depends(get_admin_user)):
    """Get full page content + related pages + sources."""
    # Path traversal protection
    if ".." in path or path.startswith("/") or "\\" in path:
        raise HTTPException(status_code=404, detail="Page not found")

    data = get_page(path)
    if data is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return data


@router.get("/search")
async def search_pages(
    q: str = Query("", min_length=1),
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_admin_user),
):
    """Full-text keyword search across all wiki pages."""
    results = search(q, limit=limit)
    return {"query": q, "results": results, "total": len(results)}


@router.get("/stats")
async def kb_stats(user: dict = Depends(get_admin_user)):
    """Knowledge base statistics."""
    return get_stats()


@router.post("/refresh")
async def refresh_index(user: dict = Depends(get_admin_user)):
    """Force rebuild the search index."""
    build_index(force=True)
    pages = discover_pages()
    return {"status": "ok", "pages_indexed": len(pages)}
