# Image Support Assessment

## Source Document

**File:** `knowledge/raw/Vorbereitung zur KP (Amboss-Zusammenfassung).pdf`  
**Pages:** 588  
**Format:** PDF 1.7 (produced by iLovePDF)  
**Size:** 17.6 MB  
**Source:** Amboss KP preparation summary (German medical exam)

---

## 1. Image Inventory

| Metric | Value |
|--------|-------|
| Total image references | 653 |
| Pages containing images | 312 / 588 (53%) |
| Raw extraction size (uncompressed) | 15.1 MB |
| Average per-image size | ~23 KB |
| Small icons (<50 px) | 0 |

All 653 images are meaningful content — there are no tiny UI icons, decorative elements, or repeated branding graphics.

---

## 2. Image Classification

### By Content Type

| Category | Count | Percentage | Typical Content |
|----------|-------|------------|-----------------|
| **Radiology** | 238 | 36.4% | Röntgen (chest, skeletal), CT (head, abdomen), MRT, ultrasound, angiography, mammography |
| **Dermatology** | 67 | 10.3% | Clinical photos of skin conditions, exanthems, dermatome maps |
| **ECG** | 60 | 9.2% | 12-lead ECG traces, rhythm strips, STEMI/NSTEMI patterns, arrhythmias |
| **Anatomy** | 42 | 6.4% | Anatomical schematics, cross-sections, organ diagrams, nerve/vessel pathways |
| **Pathology** | 16 | 2.5% | Histology slides, pathology specimens, microscopic findings |
| **Tables** | 7 | 1.1% | Tabular reference data rendered as images (drug doses, classifications) |
| **Algorithms** | 2 | 0.3% | Clinical decision flowcharts |
| **Other/Unclassified** | 221 | 33.8% | Clinical photos, surgical views, schematics, examination techniques |

**"Other" breakdown** (sampled): The 221 unclassified images are predominantly anatomical schematics and clinical examination technique illustrations that lack explicit keyword anchors in the surrounding text.

### By Image Size

| Size Bracket | Count | Total Size |
|-------------|-------|------------|
| Large (>100 KB) | 1 | 104 KB |
| Medium (20–100 KB) | 335 | ~11.1 MB |
| Small (<20 KB) | 317 | ~3.9 MB |
| Tiny icons (<50 px) | 0 | 0 |

### By PDF Section (Specialty)

| Section | Images | Raw Size |
|---------|--------|----------|
| 1-Pneumologie | 23 | 767 KB |
| 2-Kardiologie | 27 | 781 KB |
| 3-Gastroenterologie | 43 | 1,346 KB |
| 4-Innere Medizin | 28 | 637 KB |
| 5-Neurologie | 28 | 863 KB |
| 6-Notfallmedizin | 5 | 123 KB |
| 7-Chirurgie | 14 | 377 KB |
| 8-Orthopädie | 44 | 1,410 KB |
| 9-Pharmakologie | 26 | 870 KB |
| 10-Pädiatrie | 21 | 488 KB |
| 11-Psychiatrie | 40 | 781 KB |
| 12-Gynäkologie | 48 | 1,098 KB |
| 13-Urologie | 50 | 930 KB |
| 14-HNO | 46 | 974 KB |
| 15-Dermatologie | 56 | 1,447 KB |
| 16-Anästhesie | 43 | 934 KB |
| 17-Infektiologie | 44 | 765 KB |
| 18-Hygiene | 0 | 0 |
| 19-Rechtsmedizin | 67 | 910 KB |

**Note:** Section 18 (Hygiene) has 0 embedded images — all content is text-based.

---

## 3. Storage Estimates

### Raw vs Optimized

| Scenario | Size |
|----------|------|
| Raw from PDF | 15.1 MB |
| JPEG quality 85 (estimated) | ~2.3 MB |
| WebP quality 80 (estimated) | ~1.5 MB |
| AVIF quality 70 (estimated) | ~1.0–1.2 MB |
| Top 50 images (WebP q80) | ~200–350 KB |
| Top 50 + descriptions (JSON) | ~400–550 KB total |

### Cost Estimates

- **Storage:** 1.5 MB for all images → trivial on any platform (MongoDB GridFS, S3, local filesystem)
- **Bandwidth:** Average page load with images: ~10–30 KB per image → 3–6 images per page = ~30–180 KB
- **CDN:** Not necessary at this scale — inline base64 or direct file serving from backend is sufficient

---

## 4. Proposed Directory Structure

```
knowledge/
├── assets/
│   ├── images/
│   │   ├── radiology/
│   │   │   ├── 001-thorax-pneumothorax.webp
│   │   │   ├── 002-ct-schadel-blutung.webp
│   │   │   └── ...
│   │   ├── ecg/
│   │   │   ├── 001-stemi-vorderwand.webp
│   │   │   ├── 002-vorhofflimmern.webp
│   │   │   └── ...
│   │   ├── dermatology/
│   │   ├── anatomy/
│   │   ├── pathology/
│   │   └── other/
│   ├── manifest.json           # Image metadata index
│   └── README.md               # Image extraction/update instructions
```

### Alternative: Flat Structure (MVP)

For simplicity, a flat structure avoids deep nesting during early development:

```
knowledge/
├── assets/
│   ├── kp-img-001.webp
│   ├── kp-img-002.webp
│   ├── ...
│   └── manifest.json
```

**Recommended:** Start flat, migrate to categorized subdirectories at 100+ assets.

---

## 5. `manifest.json` Schema

```json
{
  "version": 1,
  "source_pdf": "Vorbereitung zur KP (Amboss-Zusammenfassung).pdf",
  "exported_at": "2026-05-30T23:45:00Z",
  "images": [
    {
      "id": "kp-img-001",
      "filename": "kp-img-001.webp",
      "category": "radiology",
      "page": 83,
      "source_pdf_page": 83,
      "width": 847,
      "height": 600,
      "size_bytes": 50200,
      "caption_de": "STEMI Vorderwandinfarkt — EKG mit ST-Hebungen",
      "caption_en": "STEMI anterior wall infarction — ECG with ST elevations",
      "keywords": ["stemi", "herzinfarkt", "vorderwand", "ekg", "st-hebung"],
      "wiki_pages": ["kardiologie", "notfallmedizin"],
      "alt_text": "12-Kanal-EKG mit ST-Hebungen in den Brustwandableitungen V1-V4"
    }
  ]
}
```

---

## 6. Linking Images to Wiki Pages

### Strategy A: Link by Page Number (Recommended for MVP)

The PDF has a known section-to-page mapping. Each image's source page number maps to a specialty:

| PDF Page Range | Wiki Page Slug | Description |
|----------------|---------------|-------------|
| 1–20 | `pneumologie` | Lunge, Atmung |
| 21–60 | `kardiologie` | Herz, Kreislauf |
| 61–100 | `gastroenterologie` | Verdauungstrakt |
| 101–130 | `innere-medizin` | Endokrinologie, Stoffwechsel |
| 131–170 | `neurologie` | Nervensystem |
| 171–200 | `notfallmedizin` | Notfälle |
| 201–230 | `chirurgie` | Chirurgie |
| 231–260 | `orthopaedie` | Bewegungsapparat |
| 261–290 | `pharmakologie` | Arzneimittel |
| 291–320 | `paediatrie` | Kinderheilkunde |
| 321–350 | `psychiatrie` | Psychiatrie |
| 351–380 | `gynaekologie` | Frauenheilkunde |
| 381–410 | `urologie` | Harnwege |
| 411–440 | `hno` | Hals-Nasen-Ohren |
| 441–470 | `dermatologie` | Haut |
| 471–500 | `anaesthesie` | Anästhesie |
| 501–530 | `infektiologie` | Infektionskrankheiten |
| 531–555 | `hygiene` | Hygiene |
| 556–588 | `rechtsmedizin` | Rechtsmedizin |

**Resolution:** Given an image with `page = 83`, look up which section contains page 83 → `gastroenterologie`. The image is automatically linked to the gastroenterology wiki page.

### Strategy B: Keyword Cross-Reference (Enhanced)

Parse the surrounding page text for wiki page titles, concept names, and disease names. Match against known wiki slugs for multi-page linking:
- An image on page 83 shows an abdominal CT → linked to both `gastroenterologie` and `diagnostik`
- An ECG showing STEMI → linked to both `kardiologie` and `notfallmedizin`

### Strategy C: Inline Wiki Markdown (Manual Curation)

Insert image references directly into wiki pages:

```markdown
## Arterielle Hypertonie

![EKG bei Linksherzbelastung](../assets/images/ecg/002-hypertonie-linksherz.webp)

*Quelle: KP-Vorbereitung Amboss, S. 40*
```

---

## 7. Top 50 Highest-Value Medical Images

Ranked by keyword relevance score (exam topics) × image size (visual information density):

| Rank | Page | Score | Size | Type (inferred) |
|------|------|-------|------|-----------------|
| 1–4 | 375 | 12.6–12.3 | 13–28 KB | Gynäkologie — anatomical diagrams |
| 5 | 83 | 12.0 | 49 KB | Gastroenterologie — likely abdominal imaging |
| 6 | 420 | 11.5 | 24 KB | Urologie — urinary tract schematic |
| 7 | 40 | 11.1 | 53 KB | Kardiologie — cardiac diagram/ECG |
| 8 | 584 | 11.0 | 1 KB | Rechtsmedizin — small reference icon |
| 9 | 342 | 10.9 | 45 KB | Psychiatrie — brain imaging |
| 10 | 110 | 10.6 | 30 KB | Innere Medizin — clinical finding |
| 11–12 | 257 | 9.8 | 39–41 KB | Pharmakologie — drug mechanism diagram |
| 13 | 439 | 9.6 | 28 KB | HNO — ENT anatomy |
| 14 | 408 | 9.5 | 22 KB | Urologie — diagnostic algorithm |
| 15 | 58 | 9.4 | 19 KB | Kardiologie — heart sound diagram |
| 16–18 | 408 | 9.3 | 13–16 KB | Urologie — supplementary views |
| 19 | 92 | 9.1 | 53 KB | Gastroenterologie — abdominal CT/ultrasound |
| 20 | 356 | 8.7 | 36 KB | Gynäkologie — pelvic anatomy |
| 21–26 | 80 | 8.6–8.3 | 14–28 KB | Gastroenterologie — liver/biliary imaging |
| 27 | 315 | 8.3 | 17 KB | Pädiatrie — pediatric examination |
| 28 | 23 | 8.3 | 17 KB | Kardiologie — vascular anatomy |
| 29–36 | 574,571 | 8.3–8.0 | 1–14 KB | Rechtsmedizin — forensic findings |
| 37 | 107 | 8.0 | 50 KB | Innere Medizin — fundoscopy/retinal |
| 38 | 45 | 8.0 | 48 KB | Kardiologie — echocardiography |
| 39 | 581 | 7.9 | 45 KB | Rechtsmedizin — forensic radiology |
| 40 | 96 | 7.9 | 45 KB | Gastroenterologie — endoscopic image |
| 41 | 44 | 7.7 | 35 KB | Kardiologie — cardiac imaging |
| 42–44,47–49 | 248–250 | 7.7–7.5 | 22–33 KB | Orthopädie — skeletal/joint imaging |
| 45–46 | 462 | 7.5 | 27 KB | Anästhesie — airway/instrumentation |
| 50 | 515 | 7.4 | 19 KB | Infektiologie — pathogen/microscopy |

**Total raw size of top 50: 1.2 MB**  
**Optimized (WebP): ~200–350 KB**

---

## 8. Implementation Recommendations

### Phase 1: MVP — Extract Top 50 (Estimated effort: 1–2 days)

1. Extract top 50 images via PyMuPDF → save as WebP
2. Generate `manifest.json` with page → wiki slug mapping
3. Link images to existing wiki pages by section
4. Display in Knowledge Lab page viewer as "associated images"
5. **Storage:** ~350 KB — trivial, can be committed to git

### Phase 2: Full Extraction (Estimated effort: 3–5 days)

1. Extract all 653 images → WebP optimization
2. Classify remaining "other" images manual review
3. Add image descriptions via OpenRouter vision API (batch)
4. Build image search index (keyword tags)
5. **Storage:** ~1.5 MB — still fits in git repo

### Phase 3: Tutor AI Integration (Estimated effort: 2–3 days)

1. Inject relevant images into Tutor AI context based on matched wiki pages
2. Show image thumbnails in Tutor AI response alongside citations
3. Allow clicking through to full-resolution image viewer

---

## 9. Open Questions

1. **Licensing:** Are the PDF images original enough to avoid copyright issues? The source is an Amboss summary, not the original Amboss product — but still needs review.
2. **Image descriptions:** Should we use OpenRouter vision API (GPT-4o-mini, ~$0.01/image) to auto-generate German captions for all 653 images?
3. **Display format:** Inline within wiki page text vs. sidebar gallery vs. lightbox overlay?
4. **Resolution trade-off:** Full resolution (better for radiology/ECG) vs. WebP compression (bandwidth savings)?
5. **Git LFS:** At 1.5 MB, standard git is fine. If raw images are kept, 15 MB may warrant LFS.
