"""Knowledge Lab — admin-only wiki browser + image gallery."""

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.staticfiles import StaticFiles
from auth import get_admin_user
from services.knowledge_lab_service import (
    discover_pages,
    get_page,
    search,
    build_index,
    get_stats,
)

router = APIRouter(prefix="/api/knowledge-lab", tags=["knowledge-lab"])

# Path to knowledge/assets/ relative to this file
_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge" / "assets"
_MANIFEST_CACHE = None


def _load_manifest():
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is None:
        manifest_path = _ASSETS_DIR / "manifest.json"
        if manifest_path.is_file():
            with open(manifest_path, "r", encoding="utf-8") as f:
                _MANIFEST_CACHE = json.load(f)
        else:
            _MANIFEST_CACHE = {"version": 2, "images": []}
    return _MANIFEST_CACHE


# Mount static file serving for images — serves /api/knowledge-lab/assets/images/...
_IMAGES_DIR = _ASSETS_DIR / "images"
if _IMAGES_DIR.is_dir():
    router.mount("/assets", StaticFiles(directory=str(_ASSETS_DIR)), name="knowledge-assets")


@router.get("/pages")
async def list_pages(user: dict = Depends(get_admin_user)):
    """List all wiki pages with metadata."""
    pages = discover_pages()
    return {"pages": pages, "total": len(pages)}


@router.get("/pages/{path:path}")
async def read_page(path: str, user: dict = Depends(get_admin_user)):
    """Get full page content + related pages + sources."""
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


@router.get("/images")
async def list_images(
    page: str = Query("", description="Wiki page slug to filter by"),
    user: dict = Depends(get_admin_user),
):
    """Get images linked to a wiki page, or all images."""
    manifest = _load_manifest()
    all_images = manifest.get("images", [])
    if page:
        filtered = [img for img in all_images if page in img.get("wiki_pages", [])]
    else:
        filtered = all_images
    return {"page": page or "all", "total": len(filtered), "images": filtered}
