---
type: index
title: Claude Code — Vault Context
status: stable
last_reviewed: 2026-05-31
tags: [type/index]
---

# Claude Code — Vault Context

You are working inside the Prep Academy knowledge vault. This is an Obsidian-managed Markdown repository — not arbitrary source code.

## Read first

1. `[[meta/conventions]]` — schema, tags, filenames, links. Source of truth for structure.
2. `[[OPERATING_MODE]]` — editorial process. When to create a page, duplicate handling, cross-link rules.
3. `[[AGENTS]]` — points back here.

## Hard rules

1. **Every new page MUST have frontmatter** matching the schema in `[[meta/conventions]]`. No exceptions.
2. **Use wikilinks** `[[page]]` for internal references. Markdown links only for external URLs.
3. **Use templates.** New pages start by copying from `templates/<type>.md`.
4. **Update `last_reviewed`** in frontmatter whenever you modify a page with `status: stable`.
5. **Do not edit `.obsidian/`** — that is Obsidian's local config, not vault content.
6. **Filenames follow the convention** in `[[meta/conventions#3-filename-conventions]]` — lowercase kebab-case, umlauts spelled out.
7. **`wiki/` stays flat for now.** Do not create subdirectories under `wiki/` (`diseases/`, `concepts/`, etc. are reserved for a future phase).
8. **Tags live in frontmatter only**, never inline in body. Use the taxonomy in `[[meta/conventions#2-tag-taxonomy]]`.

## Common operations

| Task | Steps |
|---|---|
| Create a new specialty page | Copy `templates/specialty-overview.md` → save as `wiki/<slug>.md` → fill frontmatter + body → add backlinks from related pages |
| Create a new concept page | Copy `templates/concept.md` → save as `wiki/<slug>.md` → frontmatter `type: concept` → cross-link from every specialty that uses it |
| Add a new source summary | Copy `templates/source-summary.md` → save as `wiki/sources/<slug>.md` → update `[[index]]` and `[[gaps]]` |
| Update an existing page | Read first → preserve existing structure → update `last_reviewed` → verify wikilinks resolve |
| Find work to do | Search frontmatter: `status: draft`, `status: review`, or pages where `last_reviewed` is older than 6 months |

## Do not

- Do not modify pages outside `knowledge/` from this workspace context.
- Do not move existing files (renames break links until Phase 4 ships; even then, do renames inside Obsidian so wikilinks auto-update).
- Do not delete files. Mark as `status: deprecated` instead.
- Do not invent frontmatter fields. If a need arises, propose an update to `[[meta/conventions]]` first.
- Do not modify `OPERATING_MODE.md` without explicit human approval — it is the editorial contract.

## Scope

This file applies to work inside `knowledge/`. Backend and frontend changes use the repo-root agent instructions, not this file.
