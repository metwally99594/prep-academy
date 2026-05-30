# Knowledge Base Operating Mode

## Role

Long-term knowledge base maintainer for Prep Academy. Focus on accumulation, cross-linking, and quality — not infrastructure or migration.

---

## 1. Source Ingestion Workflow

When a new source is added to `knowledge/raw/`:

1. **Read the source** — Full content scan. For PDFs >200 pages, extract table of contents + sample chapters from each section.
2. **Create source summary** — `wiki/sources/<source-name>.md` with:
   - Source metadata (filename, type, page count, language)
   - Key topics covered
   - Notable facts, scores, classifications
3. **Extract facts into existing pages** — Update relevant specialty/disease/concept pages with new information. Mark the source in an `**Sources:**` footer section.
4. **Create new pages if needed** — If the source covers a topic not yet in the wiki, create a new page.
5. **Update `gaps.md`** — Mark newly covered items as resolved; add any new gaps discovered.
6. **Update `index.md`** — Add new page to the specialty or concepts table.

**Checklist for each source:**
- [ ] Source summary created in `wiki/sources/`
- [ ] All existing pages checked for new facts
- [ ] New pages created for uncovered topics
- [ ] `gaps.md` updated
- [ ] `index.md` updated
- [ ] Cross-links added to/from new content
- [ ] Source file listed in `raw/` directory (not deleted after ingestion)

---

## 2. Updating Existing Pages

When new information becomes available for an existing topic:

1. **Read the current page** — Understand its structure and scope.
2. **Add new content** — Insert at the appropriate section. Preserve existing formatting style (tables, bullet lists, consistent heading levels).
3. **Do not bloat** — If a section exceeds ~80 lines, consider whether a separate disease page is warranted (future).
4. **Add source attribution** — Append `**Sources:** [page](sources/...)` at the bottom if the new content comes from a specific source.
5. **Update cross-links** — Ensure related pages link to the updated content.

**When to split a page:** If a single section grows to >50 lines of dense content, note it in `gaps.md` as a candidate for migration.

---

## 3. Duplicate Detection

Duplicates occur when the same fact appears in multiple specialty pages without cross-referencing.

**Detection strategy:**

| Clue | Action |
|------|--------|
| Same disease name in 2+ specialty pages | Check if it's a genuine cross-specialty topic (e.g. Diabetes in Innere Medizin + Kardiologie + Neurologie) → keep, add cross-link |
| Same fact worded differently in 2 pages | Merge into the primary page, link from the secondary page |
| Overlapping scope (e.g. "Schock" in Notfallmedizin + Chirurgie) | Keep in primary page, add a brief summary + link from secondary page |
| Identical score/classification in 2+ pages | Note in `gaps.md` as concept-page candidate |

**Before creating a new page:** grep for the topic name across `wiki/`. If found, update the existing page instead.

**Merge rule:** Primary = specialty where the disease is most central. Secondary = other specialties that encounter it → link to primary.

---

## 4. Cross-Link Maintenance

**Link freshness check (every session):**

1. Run a link scan: extract all `]()](*.md)` references from `wiki/`.
2. Verify each target file exists.
3. If a file was renamed/deleted, update all referrers.

**Cross-link density target:**
- Each specialty page: ≥6 outgoing links to other specialty/concept pages
- Each concept page: ≥4 outgoing links
- Each source summary: link to every page it contributes data to

**Backlink convention:** Add a `**Related Pages:**` section at the bottom of every page. List pages that link *to* this page (backlinks) when practical.

**New page rule:** Every new page must link to at least 3 existing pages and be linked from at least 1 existing page.

---

## 5. Keeping `gaps.md` Updated

`gaps.md` is the inventory of work not yet done. It must reflect reality after every session.

**Update triggers:**
- After creating a new page → remove from gaps
- After expanding a page to cover a noted gap → mark as covered
- After ingesting a new source → add any newly discovered gaps
- After architecture discussion → add/remove gaps as priorities shift

**Format:** Keep the priority ordering (High / Medium). Remove items only when fully covered, not when partially addressed.

**Don't delete gaps:** Instead of deleting, mark as `[covered]`. This preserves the history of what was once missing.

---

## 6. Using `roadmap.md`

`roadmap.md` is the future target — NOT the current plan.

**When to reference it:**
- When deciding whether to split a page (does writing fit the planned disease/concept split?)
- When creating new pages (should this be in `specialties/`, `diseases/`, or `concepts/`?)
- When new sources reveal structural problems not anticipated by the roadmap

**Current rule:** Do not implement any directory restructuring. Keep everything flat in `wiki/`. Create new files in `wiki/`. Let the roadmap inform design decisions but not constrain them.

---

## 7. Source Page Tracking

Every source in `raw/` must have a corresponding summary in `wiki/sources/`.

**Source page checklist:**
- [ ] Source metadata (filename, date of ingestion, size/type)
- [ ] Topics covered (matching specialty pages)
- [ ] Notable facts not yet extracted
- [ ] Link to the raw file (`../raw/...`)
- [ ] Links to all specialty pages that use data from this source

**Discoverability:** The source summary is the bridge between the raw document and the structured wiki. If a user wants to know "what does the Amboss PDF say about X?" they start at the source summary, follow the link to the specialty page, and see the extracted content with source attribution.

---

## 8. Quality Checks Before Modifying

Before any edit to the wiki:

1. **Read current file** — Confirm the exact content before editing. Never edit from memory.
2. **Check for stale information** — Does the edit contradict existing content? If so, reconcile or note the discrepancy.
3. **Verify links** — Every `](page.md)` reference must resolve. For relative links, confirm from the editing file's directory.
4. **Format consistency** — Match the existing style: heading hierarchy, table style (pipe alignment), bullet indentation.
5. **Source attribution** — If the edit introduces new facts not from an ingested source, mark it with a note.
6. **No dead ends** — Every page should have at least one link to another page in the wiki.

**After every session:**
- [ ] All links verified
- [ ] `gaps.md` reflects new state
- [ ] `index.md` includes any new pages
- [ ] No orphan pages (pages with 0 incoming links)
