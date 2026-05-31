---
type: index
title: Vault Conventions
status: stable
last_reviewed: 2026-05-31
tags: [type/index]
---

# Vault Conventions

Authoritative reference for vault structure, frontmatter, tags, filenames, and links. All AI agents and human editors follow this.

For the editorial process (when to create vs. update a page, duplicate handling, cross-link rules), see `[[OPERATING_MODE]]`.

## 1. Frontmatter schema

Every page MUST start with a YAML frontmatter block.

| Field | Type | Required | Notes |
|---|---|---|---|
| `type` | enum | yes | One of: `disease`, `specialty`, `concept`, `source`, `licensing`, `qa-report`, `roadmap`, `index`, `template`, `daily` |
| `title` | string | yes | Canonical display name. Used by the Knowledge Lab as the page title. |
| `aliases` | list of strings | no | Alternate names. Enables Obsidian autocomplete on `[[`. |
| `specialty` | list of strings | conditional | Required on `disease`. Recommended on cross-cutting `concept`. Values from the specialty slug list in §2. |
| `exam_relevance` | enum | no | `high`, `medium`, `low`. Default `medium`. |
| `status` | enum | yes | `draft`, `review`, `stable`, `stale`, `deprecated`. See §5. |
| `last_reviewed` | date | yes | `YYYY-MM-DD`. Update when content is touched. |
| `sources` | list of wikilinks | no | E.g. `["[[sources/kp-vorbereitung-amboss]]"]`. |
| `tags` | list of strings | yes | See §2. |
| `icd10` | string or list | no | Disease pages only. |
| `related` | list of wikilinks | no | Machine-readable mirror of `## Related Pages`. |

Notes:
- Wikilinks inside YAML are quoted strings — they are not parsed as links by Obsidian, they're free-form text that tools may interpret.
- Unknown fields are tolerated but should not be added without updating this doc first.

## 2. Tag taxonomy

Tags use Obsidian's hierarchical syntax with `/`. All tags live in frontmatter, never inline in body.

| Branch | Allowed leaves |
|---|---|
| `exam/` | `kp`, `fsp`, `kmp-innsbruck`, `fachpruefung` |
| `specialty/` | `kardiologie`, `pneumologie`, `gastroenterologie`, `innere-medizin`, `neurologie`, `notfallmedizin`, `chirurgie`, `orthopaedie`, `pharmakologie`, `paediatrie`, `psychiatrie`, `gynaekologie`, `urologie`, `hno`, `dermatologie`, `anaesthesie`, `infektiologie`, `hygiene`, `rechtsmedizin`, `diagnostik`, `biostatistik`, `klinische-untersuchung`, `praevention`, `nostrifikation` |
| `type/` | mirrors the `type` frontmatter field |
| `status/` | mirrors the `status` frontmatter field |
| `priority/` | `p0`, `p1`, `p2` (roadmap items only) |
| `source/` | `amboss`, `herold`, `eric`, `s3-leitlinie`, `who`, `rki`, `nklm`, `aerzteg` |

Every page must carry at least `type/<type>` and `status/<status>`. Specialty/disease pages add `specialty/<slug>`. KP-exam-relevant pages add `exam/kp`.

## 3. Filename conventions

- Lowercase, kebab-case: `asthma-bronchiale.md`, not `Asthma-Bronchiale.md`, not `asthma_bronchiale.md`.
- German umlauts spelled out: `ä → ae`, `ö → oe`, `ü → ue`, `ß → ss`. Follow existing precedent in the vault: `paediatrie`, `gynaekologie`, `praevention`, `anaesthesie`.
- No spaces. No leading or trailing dashes.
- Extension `.md`.
- Index pages in a folder are named `_index.md` so they sort first.

## 4. Link conventions

| Use case | Syntax |
|---|---|
| Internal page reference (default) | `[[asthma-bronchiale]]` |
| Internal page with custom display text | `[[asthma-bronchiale\|Asthma]]` |
| Reference in a subfolder | `[[sources/kp-vorbereitung-amboss]]` |
| Section anchor | `[[scores-und-klassifikationen#NYHA]]` |
| Embed a section (rendered in Obsidian) | `![[scores-und-klassifikationen#NYHA]]` |
| External URL | `[Amboss](https://www.amboss.com/...)` |
| Image | `![Beschreibung](../assets/images/ekg-stemi.webp)` |

Rules:
- Wikilinks are the default for any link to another vault page.
- Markdown links are reserved for external URLs and (for now) images.
- Image link convention may change in a later phase. Do not migrate existing image links yet.

## 5. Status lifecycle

```
draft ──► review ──► stable ──┬──► stale ──► review ──► stable
                              │
                              └──► deprecated  (terminal)
```

- `draft` — new page, content incomplete.
- `review` — content complete, awaiting editorial review.
- `stable` — reviewed, considered current.
- `stale` — `last_reviewed` older than 6 months. Schedule revisit.
- `deprecated` — kept for backlinks; do not link new pages to it.

## 6. Page anatomy by type

Templates in `templates/` are the source of truth for required sections per page type. Copy the matching template when creating a new page rather than reconstructing the structure from memory.

Body always starts with `# {{title}}` matching the frontmatter `title`.

## 7. Quick reference card

When creating a new page:

1. Copy the appropriate template from `templates/`.
2. Fill frontmatter — required: `type`, `title`, `status`, `last_reviewed`, `tags`.
3. Use wikilinks for any reference to another vault page.
4. Add at least 3 outgoing links (per `[[OPERATING_MODE]]` rule).
5. Ensure at least 1 existing page links to this new page.
6. Quick visual check in Obsidian: graph view, backlinks panel.
