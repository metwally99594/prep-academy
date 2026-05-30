# Wiki Architecture Roadmap

**Status: Future target — do not refactor until ≥20–30 sources are indexed.**

## Current Structure (keep using)

```
knowledge/
├── AGENTS.md
├── index.md
├── roadmap.md            ← this file
├── raw/                  ← source documents
└── wiki/
    ├── sources/          ← source summaries
    └── *.md              ← flat specialty pages (nostrifikation, pneumologie, etc.)
```

## Why Not Refactor Now

The flat structure has three advantages at this stage:

1. **Low friction**: One file per specialty, easy to create, edit, and cross-link. No navigation overhead.
2. **Validation first**: We need to see how the wiki grows under real use — which topics get deep, which stay shallow, what cross-links emerge naturally. Premature refactoring risks carving directories around assumptions that don't hold.
3. **Link stability**: Every restructure breaks every internal link. Until we have confidence in the content boundaries, moving files creates maintenance debt without proven benefit.

The threshold of 20–30 sources is a heuristic: by then we'll see which specialties have 1 disease vs. 10+, which concepts repeat across files, and whether the flat `wiki/` directory is already hard to navigate.

## Observed Problems That Drive the Target

| Problem | Current Example | Target Fix |
|---------|----------------|------------|
| Mixed granularity | `pneumologie.md` packs 7 diseases inline | `specialties/pneumologie.md` → overview, `diseases/asthma-bronchiale.md` → detail |
| Missing specialties | 10 of ~20 areas from source have no page | `specialties/` gets full coverage per source catalogue |
| Grab-bag pages | `innere-medizin.md` = diabetes + thyroid + nephrology + adrenal in one file | Split into `endokrinologie.md`, `nephrologie.md` |
| No cross-cutting references | EKG is in `diagnostik.md`; scores are scattered across 6 files | `concepts/ekg-grundlagen.md`, `concepts/scores-und-klassifikationen.md` |
| Flat directory | All files in `wiki/` | `specialties/`, `diseases/`, `concepts/` subdirectories |
| Manual cross-links | 35 hard-coded links, no backlink tracking | Migrate only when content boundaries are stable |

## Target Structure (when ready)

```
knowledge/
├── AGENTS.md
├── index.md                        ← portal
├── roadmap.md
├── raw/
└── wiki/
    ├── licensing/                  ← degree recognition pathway
    │   ├── nostrifikation.md
    │   └── stichprobentest.md
    ├── sources/                    ← source summaries (unchanged)
    ├── specialties/                ← overviews per specialty
    │   ├── index.md                ← TOC of all specialties
    │   ├── pneumologie.md
    │   ├── kardiologie.md
    │   ├── gastroenterologie.md
    │   ├── endokrinologie.md       ← split from innere-medizin
    │   ├── nephrologie.md          ← split from innere-medizin
    │   ├── neurologie.md
    │   ├── notfallmedizin.md
    │   ├── chirurgie.md
    │   ├── orthopaedie.md
    │   ├── paediatrie.md
    │   ├── gynaekologie.md
    │   ├── psychiatrie.md
    │   ├── urologie.md
    │   ├── hno.md
    │   ├── dermatologie.md
    │   ├── anaesthesie.md
    │   ├── infektiologie.md
    │   └── rechtsmedizin.md
    ├── diseases/                   ← one page per disease
    │   ├── asthma-bronchiale.md
    │   ├── copd.md
    │   ├── lungenembolie.md
    │   ├── pneumonie.md
    │   ├── lungenkarzinom.md
    │   ├── herzinsuffizienz.md
    │   ├── koronare-herzkrankheit.md
    │   ├── vorhofflimmern.md
    │   ├── diabetes-mellitus.md
    │   ├── schlaganfall.md
    │   ├── epilepsie.md
    │   ├── morbus-parkinson.md
    │   ├── leberzirrhose.md
    │   ├── niereninsuffizienz.md
    │   ├── osteoporose.md
    │   └── ... (per condition)
    └── concepts/                   ← cross-cutting references
        ├── scores-und-klassifikationen.md
        ├── antibiotika.md
        ├── laborreferenz.md
        ├── ekg-grundlagen.md
        ├── impfkalender.md
        ├── klinische-untersuchung.md
        └── differenzialdiagnosen-index.md
```

### Page Roles (in target)

| Layer | Purpose | Links to |
|-------|---------|----------|
| `specialties/*` | Scope, sub-areas, key diseases, exam weight | `diseases/*`, `concepts/*` |
| `diseases/*` | Full entry: definition, ICD, pathophysiology, diagnostics, therapy, KP tips, DD | `specialties/*` (backlink), `concepts/*`, other `diseases/*` |
| `concepts/*` | Reusable reference: score tables, drug classes, lab ranges, algorithms | `specialties/*`, `diseases/*` |

## Migration Plan (when ready)

### Phase 1 — Directory scaffold
**Move existing files into `specialties/`; update all internal links.**
- Why separate: every restructure breaks links. Doing it in one batch minimizes disruption and lets us validate all paths at once.
- Creates `specialties/`, `diseases/`, `concepts/` directories.
- Existing files (nostrifikation.md, pneumologie.md, etc.) move to `specialties/` or `licensing/`.
- All `related pages` links across all files updated to use new relative paths.
- `index.md` and source summary links updated.

### Phase 2 — Convert specialty pages → overviews
**Trim each to scope + disease table with `diseases/*` links.**
- Reason: today's specialty pages mix overview + disease detail. Splitting makes each page easier to maintain and read.
- Each overview defines what the specialty covers, lists key diseases with links, notes KP exam weight.
- All disease-specific content (pathophysiology, diagnostics, therapy tables) is lifted out.

### Phase 3 — Create disease pages
**Extracted disease content goes into `diseases/*.md` with a standard template.**
- Reason: consistent structure makes scanning fast. Every disease page answers the same questions: definition, diagnostics, therapy, KP tips.
- Template: `# Disease Name` → ICD → Pathophysiology → Diagnostics → Therapy (acute/chronic) → Differential diagnoses → KP tips → Related pages.
- ~15 initial pages from current content; ~30 more from source as we write them.

### Phase 4 — Extract concept pages
**Pull cross-cutting content out of specialty pages into `concepts/`.**
- Reason: scores (CRB-65, CHADS₂VASc, ABCD², GCS, NYHA, Child-Pugh) appear in 6+ files — updating one score means touching 6 files. A single concept page eliminates duplication.
- Candidates: EKG aus `kardiologie.md` + `diagnostik.md`, antibiotics aus `pharmakologie.md`, lab reference aus `diagnostik.md`, scores from everywhere.

### Phase 5 — Fill missing specialties
**Create overview pages for specialties listed in the source but missing from the wiki.**
- Reason: the source catalogue has ~20 areas; only 10 are covered. Gaps mean uneven exam prep.
- Pädiatrie, Gynäkologie, Psychiatrie, Urologie, HNO, Dermatologie, Anästhesie, Infektiologie, Hygiene, Rechtsmedizin.
- Each starts as a skeleton with basic scope and link to source summary; disease pages added as content warrants.

### Phase 6 — Update index.md
**Replace flat table with `specialties/` and `concepts/` navigation.**
- Reason: a flat table of 30+ rows is overwhelming. Grouping by `specialties/` (list) and `concepts/` (quick reference) is scannable.

## Current Focus

Knowledge accumulation, source ingestion, cross-linking, and updating existing pages — using the **current flat structure**. The target architecture stays on paper until the repo reaches 20–30+ sources and content boundaries are proven stable.
