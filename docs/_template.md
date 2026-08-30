---
title: New Procedure
category: Operations
order: 100
description: One sentence describing what this document covers.
---

# New Procedure

<!--
Copy this file to docs/<something>.md to start a new document. The leading
underscore keeps this template off the site — build_docs_index.py treats
`_`-prefixed files as drafts.

The front matter above is entirely optional. Without it:
  title       ← the first `# H1` below, else the filename
  category    ← the subdirectory name, else "General"
  order       ← 100 (ties break alphabetically by title)
  description ← the first paragraph of prose

Everything else is ordinary Markdown: headings, tables, code, links.
`- [ ]` items render as checkboxes you can actually tick, and the ticks are
remembered on that device — good for checklists you run every departure.

Links to other documents work with a plain relative path, e.g.
[the systems overview](systems.md); the reader keeps you inside the app.

Status tags mark the state of an item inline — see the legend at the top
of systems.md. Use them by dropping the raw HTML span into the Markdown
(marked/DOMPurify pass both through):
  <span class="doc-tag doc-tag--issue">Unresolved</span>
  <span class="doc-tag doc-tag--partial">Partial Fix</span>
  <span class="doc-tag doc-tag--planned">Planned</span>
  <span class="doc-tag doc-tag--maintenance">Maintenance</span>
Every doc-tag--planned item should also appear on planned-projects.md, and
every doc-tag--maintenance item on maintenance.md.
-->

Why this procedure exists and when to run it.

## Before you start

- [ ] Something to confirm first
- [ ] Something else

## Procedure

1. First step.
2. Second step.

## If it goes wrong

What to check, and who to call.
