# Image Integration — Implementation Proposal

**Phase:** 2 (Top 50 highest-value medical images)  
**Based on:** `IMAGE_SUPPORT_REPORT.md` (653 images assessed, top 50 ranked)  
**Status:** Proposal — ready for approval

---

## 1. Extraction Plan

### Tooling
- **PyMuPDF (fitz)** — already installed (`import fitz`)
- **Pillow** — already installed (`PIL`)
- **WebP** — lossy compression via `PIL.Image.save()` with `"webp"` format, `quality=80`

### Script: `backend/scripts/extract_top50_images.py`

```
knowledge/
├── scripts/
│   └── extract_images.py          # extraction + manifest generation
```

**Algorithm:**
1. Open PDF (`knowledge/raw/Vorbereitung zur KP (Amboss-Zusammenfassung).pdf`)
2. For each of the top 50 page numbers (from IMAGE_SUPPORT_REPORT.md):
   - Render page via `fitz.Page.get_pixmap(dpi=200)` → PIL Image
   - Crop embedded images by detecting non-text regions:
     - Use `fitz.Page.get_image_info()` or
     - Page-level rendering + contour detection (find bounding boxes of image regions)
   - Alternative: render entire page at 200 DPI and store as-is (simpler, but includes text context)
   - **Recommended approach**: Render full page at 200 DPI → crop to image bounding boxes using PyMuPDF's `get_image_bbox()` method. This extracts only the visual content, not the surrounding text.
3. Convert to WebP (`PIL.Image.save(fp, "webp", quality=80)`)
4. Save to `knowledge/assets/images/kp-img-NNN.webp`
5. Append metadata to `manifest.json`

### Image Cleanup
- Ignore images < 5 KB after compression (likely tiny icons or artifacts)
- Skip pages where no embedded image is found (page-level rendering has no image regions)
- Log skipped pages for manual review

### Edge Cases
- **Page with multiple images**: Extract each separately → `kp-img-001a.webp`, `kp-img-001b.webp`
- **Full-page image**: No crop needed — save page render directly
- **Blank/decorative image**: Skip if dimensions < 100×100 after crop
- **Duplicate images**: Hash-compare extracted image bytes → deduplicate

---

## 2. Storage Structure

### Flat Structure (Phase 2 — MVP)

```
knowledge/
├── assets/
│   ├── images/
│   │   ├── kp-img-001.webp
│   │   ├── kp-img-002.webp
│   │   ├── ...
│   │   └── kp-img-050.webp
│   ├── manifest.json              # ← canonical metadata index
│   └── README.md                  # extraction workflow instructions
```

### Design Rationale
- **Flat is simpler** for MVP (no subdirectory routing needed)
- **50 files × ~5 KB each** = ~350 KB — trivial for git
- **Migration path**: At 100+ assets, move to categorized subdirectories:
  ```
  knowledge/assets/images/
  ├── radiology/
  ├── ecg/
  ├── dermatology/
  ├── anatomy/
  └── other/
  ```
  This migration only changes `manifest.json` `filename` values — no code changes needed.

### Git Storage
- Total size: ~350 KB (optimized WebP) + 50 KB (manifest)
- **No LFS needed** — standard git handles this easily
- Can be committed to `main` directly

---

## 3. Manifest Format

### Schema (`knowledge/assets/manifest.json`)

```json
{
  "version": 2,
  "source_pdf": "Vorbereitung zur KP (Amboss-Zusammenfassung).pdf",
  "exported_at": "2026-06-01T00:00:00Z",
  "total_images": 50,
  "images": [
    {
      "id": "kp-img-001",
      "filename": "kp-img-001.webp",
      "category": "radiology",
      "pdf_page": 375,
      "width": 800,
      "height": 600,
      "size_bytes": 12400,
      "caption_de": "Anatomische Darstellung der weiblichen Beckenorgane",
      "keywords": ["becken", "anatomie", "gynäkologie", "uterus", "ovarien"],
      "wiki_pages": ["gynaekologie"],
      "alt_text": "Schematische Darstellung des weiblichen Beckens mit Uterus, Ovarien und Tuben"
    }
  ]
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier (`kp-img-NNN`) |
| `filename` | string | yes | Relative path within `images/` |
| `category` | string | yes | One of: `radiology`, `ecg`, `dermatology`, `anatomy`, `pathology`, `table`, `algorithm`, `other` |
| `pdf_page` | integer | yes | Source PDF page number |
| `width` | integer | yes | Image width in pixels |
| `height` | integer | yes | Image height in pixels |
| `size_bytes` | integer | yes | File size in bytes |
| `caption_de` | string | recommended | German caption |
| `keywords` | string[] | recommended | Search keywords |
| `wiki_pages` | string[] | recommended | Linked wiki page slugs |
| `alt_text` | string | recommended | Accessibility alt text |
| `source_pdf_page` | integer | optional | If image spans multiple pages |

### Manifest v1 → v2 Diff
- **v1** (from proposal): `source_pdf_page` → renamed to `pdf_page` (shorter)
- **v1**: required `caption_en` → **v2**: removed (German-only MVP)
- **v2 new**: `keywords` for search indexing
- **v2 new**: `wiki_pages` for page linking (array — one image can link to multiple wiki pages)

---

## 4. Mapping Strategy: PDF Page → Image → Wiki Page

### Strategy A: Page-Number-to-Specialty Lookup (MVP)

The PDF section-to-page mapping from IMAGE_SUPPORT_REPORT.md is implemented as a lookup table:

```python
# backend/services/image_mapping.py

PAGE_SPECIALTY_MAP = [
    (1, 20,   "pneumologie"),
    (21, 60,  "kardiologie"),
    (61, 100, "gastroenterologie"),
    (101, 130, "innere-medizin"),
    (131, 170, "neurologie"),
    (171, 200, "notfallmedizin"),
    (201, 230, "chirurgie"),
    (231, 260, "orthopaedie"),
    (261, 290, "pharmakologie"),
    (291, 320, "paediatrie"),
    (321, 350, "psychiatrie"),
    (351, 380, "gynaekologie"),
    (381, 410, "urologie"),
    (411, 440, "hno"),
    (441, 470, "dermatologie"),
    (471, 500, "anaesthesie"),
    (501, 530, "infektiologie"),
    (531, 555, "hygiene"),
    (556, 588, "rechtsmedizin"),
]


def page_to_wiki_slugs(page_num: int) -> list[str]:
    """Map a PDF page number to one or more wiki page slugs."""
    slugs = []
    for start, end, slug in PAGE_SPECIALTY_MAP:
        if start <= page_num <= end:
            slugs.append(slug)
    return slugs
```

### Strategy B: Keyword Enrichment (Phase 3)

After MVP, enhance mapping by:
1. Reading surrounding page text (50 lines before/after image)
2. Matching known wiki page titles, disease names, and concept names
3. Adding matched pages to `wiki_pages[]` in manifest

Example: An ECG on page 44 falls in "Kardiologie" range, but also references "Notfallmedizin" (STEMI). After enhancement:
- `wiki_pages: ["kardiologie", "notfallmedizin"]`

### Strategy C: Inline Wiki Embedding (Phase 4)

Insert image references directly into wiki markdown:
```markdown
## STEMI

![STEMI Vorderwandinfarkt](../assets/images/kp-img-007.webp)
*Quelle: KP-Vorbereitung Amboss, S. 44*
```

This is the most precise but most labor-intensive — requires manual placement.

---

## 5. Knowledge Lab Image Rendering Design

### Backend: New Endpoint

**Add to `knowledge_lab.py`:**
```
GET /api/knowledge-lab/images?page={wiki_slug}
```

Returns images linked to a given wiki page:
```json
{
  "page": "kardiologie",
  "images": [
    {
      "id": "kp-img-007",
      "filename": "kp-img-007.webp",
      "category": "ecg",
      "caption_de": "STEMI Vorderwandinfarkt — EKG mit ST-Hebungen",
      "width": 847,
      "height": 600,
      "size_bytes": 15200
    }
  ]
}
```

**Data source:** Read from `knowledge/assets/manifest.json` and filter by `wiki_pages` array.

**Image serving:**
- Option A (MVP): Base64 inline — embedding `data:image/webp;base64,...` in JSON response. Simple but adds ~15 KB per image to response.
- Option B (Recommended): Static file serving — add FastAPI `StaticFiles` mount at `/api/knowledge-lab/assets/images/`. Lighter payload, allows caching. Requires backend path to `knowledge/assets/`.

**Recommended: Option B** (static file mount):
```python
from fastapi.staticfiles import StaticFiles
import os

assets_path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "assets")
router.mount("/assets", StaticFiles(directory=assets_path), name="knowledge-assets")
```

Images served at: `https://prep-academy.onrender.com/api/knowledge-lab/assets/images/kp-img-007.webp`

### Frontend: KBPageViewer Enhancement

**New component: `KBImageGallery`** — displayed between page content and related pages in `KBPageViewer`.

```
┌──────────────────────────────────────┐
│  Kardiologie (page content)          │
│  ─────────────────────────────       │
│  ...                                 │
│                                      │
│  ── Associated Images ──             │
│  ┌──────────┐ ┌──────────┐          │
│  │ thumbnail│ │ thumbnail│          │
│  │ 120×90   │ │ 120×90   │          │
│  │ STEMI    │ │ Vorhof-  │          │
│  │ EKG      │ │ flimmern │          │
│  └──────────┘ └──────────┘          │
│  ┌──────────┐                        │
│  │ thumbnail│                        │
│  │ 120×90   │                        │
│  │ Echo     │                        │
│  └──────────┘                        │
│                                      │
│  ── Related Pages ──                 │
│  ...                                 │
└──────────────────────────────────────┘
```

**States:**
- **Loading**: Skeleton placeholder (3 rounded rectangles 120×90)
- **Empty**: Section hidden entirely (no "Associated Images" heading)
- **Error**: Inline error message "Image could not be loaded" with fallback icon
- **Normal**: Grid of thumbnails, click to open lightbox

**Interaction:**
- Click thumbnail → ImageLightbox overlay (full-resolution with caption)
- Hover → 0.2s scale(1.05) transition, caption tooltip
- Lightbox → close on backdrop click or Escape key

### Lightbox Component (reuse existing pattern)

Reuse the same lightbox pattern from `AIChat.jsx` (lines 764-788):
```jsx
{lightboxImage && (
  <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
    onClick={() => setLightboxImage(null)}>
    <div className="max-w-4xl max-h-[90vh] relative" onClick={e => e.stopPropagation()}>
      <img src={imageUrl} alt={caption} className="max-w-full max-h-[85vh] object-contain rounded-lg" />
      <div className="text-white/70 text-sm mt-2 text-center">{caption}</div>
    </div>
  </div>
)}
```

---

## 6. Tutor AI Image Citation Design

### Backend: Image Injection in Tutor Response

**New function in `ai_tutor()` flow:**

```
ai_tutor(user_message)
├── _search_wiki()          ← keyword search (existing)
├── search_chapters()       ← Qdrant vector search (existing)
├── _get_relevant_images(wiki_sources)  ← NEW
│   └── Read manifest.json
│   └── Filter images by wiki_pages matches
│   └── Return top 2-3 images per matched wiki page
└── Build response
    ├── wiki_sources        ← (existing)
    ├── evidence            ← (existing)
    ├── wiki_images         ← NEW: [{id, filename, caption_de, url}]
    └── response            ← (existing, with image citations)
```

**`_get_relevant_images()` logic:**
```python
async def _get_relevant_images(wiki_sources: list[dict]) -> list[dict]:
    """Find images linked to matched wiki pages."""
    matched_slugs = {s["path"] for s in wiki_sources}
    images = load_manifest()["images"]
    relevant = [img for img in images if set(img["wiki_pages"]) & matched_slugs]
    # Sort by relevance: prefer images that match more wiki_pages
    relevant.sort(key=lambda img: len(set(img["wiki_pages"]) & matched_slugs), reverse=True)
    return relevant[:3]  # max 3 images per response
```

**Response payload addition:**
```json
{
  "response": "...",
  "wiki_sources": [...],
  "evidence": [...],
  "wiki_images": [
    {
      "id": "kp-img-007",
      "filename": "kp-img-007.webp",
      "url": "/api/knowledge-lab/assets/images/kp-img-007.webp",
      "caption_de": "STEMI Vorderwandinfarkt — EKG mit ST-Hebungen",
      "category": "ecg"
    }
  ]
}
```

### Frontend: AIChat Wiki Image Rendering

**New section in `AIChat.jsx` — after wiki_sources, before evidence:**

```jsx
{message.wiki_images && message.wiki_images.length > 0 && (
  <div className="mt-3 space-y-2">
    <p className="text-[11px] font-semibold text-white/30 uppercase tracking-wider">
      Medizinische Abbildungen
    </p>
    <div className="flex flex-wrap gap-2">
      {message.wiki_images.map((img, i) => (
        <div key={i} className="relative cursor-pointer group"
            onClick={() => setLightboxImage({
              url: img.url,
              title: img.caption_de,
              _source: 'Wissensdatenbank'
            })}>
          <img src={img.url} alt={img.caption_de || ''}
            className="w-[120px] h-[90px] object-cover rounded-lg border"
            style={{ borderColor: 'rgba(59,130,246,0.2)' }}
            loading="lazy" />
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors rounded-lg" />
        </div>
      ))}
    </div>
  </div>
)}
```

**Edge cases:**
- **No wiki images found**: Section hidden entirely (empty array check)
- **Image load failure**: `onError` handler swaps to a placeholder icon
- **Slow network**: `loading="lazy"` defers off-screen images
- **Accessibility**: `alt` text from manifest is used

### Response rendering order in AIChat

```
┌─────────────────────────────┐
│  Message text content       │
│                             │
│  ── MCQ Analysis ──         │  (if present)
│  ── Images from PDF ──     │  (existing — uploaded doc images)
│  ── Medizinische            │
│     Abbildungen ──          │  ← NEW: wiki images
│  ── Quellen ──              │  (existing — document evidence)
│  ── Wissensdatenbank ──     │  (existing — wiki sources)
└─────────────────────────────┘
```

---

## 7. Estimated Implementation Effort

### Phase 2 — Top 50 Images (MVP)

| Task | Files | Effort | Complexity |
|------|-------|--------|------------|
| 1. Extraction script | `backend/scripts/extract_images.py` | 2–3 hrs | Medium |
| 2. Generate manifest.json | (generated by script) | 30 min | Low |
| 3. Serve images via static mount | `backend/routes/knowledge_lab.py` | 30 min | Low |
| 4. Image lookup endpoint | `backend/routes/knowledge_lab.py` + `backend/services/image_mapping.py` | 1 hr | Low |
| 5. KBImageGallery component | `frontend/src/pages/KnowledgeLabPage.jsx` (+~120 lines) | 1.5 hrs | Medium |
| 6. Image lightbox | Reuse existing pattern (~30 lines) | 30 min | Low |
| 7. Tutor AI image injection | `backend/server.py` (ai_tutor function) | 1 hr | Medium |
| 8. Frontend image citations | `frontend/src/components/AIChat.jsx` (+~40 lines) | 1 hr | Low |

**Total Phase 2: ~8 hours** (1 full day)

### Dependencies

| Dependency | Version | Currently Installed? |
|------------|---------|---------------------|
| PyMuPDF (fitz) | ≥1.23 | ✅ Yes |
| Pillow | ≥10.0 | ✅ Yes |
| WebP support in PIL | (built into Pillow) | ✅ Yes |

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Image bounding boxes overlap text | Cropped images contain text | Use `get_image_bbox()` with padding reduction; fall back to page-level render if no embedded images found |
| WebP quality too low for radiology | Diagnostic images unusable | Use quality=85 for radiology/ECG category; quality=70 for illustrations |
| Static file mount path differs in production | 404 errors | Use env var `KNOWLEDGE_ASSETS_DIR` with fallback relative path |
| Manifest grows stale after wiki reorganization | Images linked to wrong pages | `wiki_pages` field is denormalized — update on wiki page rename/move |

### Future Phases

| Phase | Scope | Effort | When |
|-------|-------|--------|------|
| **Phase 3** | Full extraction (all 653 images) + categorization | 3–5 days | After Phase 2 validated |
| **Phase 4** | Inline wiki markdown embedding + keyword cross-ref enrichment | 2–3 days | After Phase 3 |
| **Phase 5** | Image search index (keyword/tag search in Knowledge Lab) | 1–2 days | After Phase 4 |
| **Phase 6** | OpenRouter vision API auto-captioning (GPT-4o-mini, ~$0.01/image) | 1 day | Optional |

---

## Appendix: Wiki Page ⇄ Specialty Mapping (from IMAGE_SUPPORT_REPORT.md)

| PDF Pages | Wiki Slug | Specialty |
|-----------|-----------|-----------|
| 1–20 | `pneumologie` | Pulmonology |
| 21–60 | `kardiologie` | Cardiology |
| 61–100 | `gastroenterologie` | Gastroenterology |
| 101–130 | `innere-medizin` | Internal Medicine |
| 131–170 | `neurologie` | Neurology |
| 171–200 | `notfallmedizin` | Emergency Medicine |
| 201–230 | `chirurgie` | Surgery |
| 231–260 | `orthopaedie` | Orthopedics |
| 261–290 | `pharmakologie` | Pharmacology |
| 291–320 | `paediatrie` | Pediatrics |
| 321–350 | `psychiatrie` | Psychiatry |
| 351–380 | `gynaekologie` | Gynecology |
| 381–410 | `urologie` | Urology |
| 411–440 | `hno` | ENT |
| 441–470 | `dermatologie` | Dermatology |
| 471–500 | `anaesthesie` | Anesthesiology |
| 501–530 | `infektiologie` | Infectious Diseases |
| 531–555 | `hygiene` | Hygiene |
| 556–588 | `rechtsmedizin` | Forensic Medicine |
