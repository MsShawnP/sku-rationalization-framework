---
title: CSS design token drift in Lailara projects
date: 2026-05-28
last_updated: 2026-07-28
category: conventions
module: app/css/lailara.css
problem_type: convention
component: tooling
severity: medium
applies_when:
  - Writing or extending CSS for any Lailara design system project
  - Before milestone commits, version tags, or PRs touching CSS
  - After any session where new CSS rule bodies were authored
  - When adding a new component to an existing Lailara project
  - When a design system update is published
tags:
  - css
  - design-tokens
  - color
  - lailara
  - hex
  - custom-properties
  - convention
  - frontend
---

# CSS design token drift in Lailara projects

**Moved 2026-07-28. Canonical location: `~/projects/reference/lailara-design-system/CSS_TOKEN_AUDIT.md`.**

The full rule, the six-step audit procedure, the five failure modes with before/after CSS, and the cache-busting verification all live there, next to the `LAILARA_DESIGN_SYSTEM.md` they enforce. This file is a pointer — do not restate the content here, and do not let the two drift.

## Why it moved

This document's own `applies_when` declared portfolio scope in four of five lines — "any Lailara design system project," "when a design system update is published" — while the file sat in one project's `docs/solutions/conventions/`. `docs/solutions/` is per-repo with no shared location, so a rule governing every Lailara project was visible only to a session working in this one.

That is the same defect the rule itself is about, one layer up: guidance scoped to the surface where it was learned rather than the surface it governs. See `~/projects/reference/prevention-rule-scoping.md`.

## What stays here

The incident that produced it. During V1 implementation of this tool, `app/css/lailara.css` was authored without a design system audit pass, and five deviations accumulated: an invented token (`--canvas-hover: #faf9f6`), two values off by 1–3 hex digits (`#e5e8f5` for Chicago-95, `#fde8e7` for Red-95), an inline `rgba()` duplicating the existing `--card-border` token, and a print shorthand (`#333`) plus a 4px mobile `border-radius` over the 2px cap.

`/ce:review` surfaced the most visible case — an amber `#c87e0d` not in the palette at all. A full audit against `LAILARA_DESIGN_SYSTEM.md` found the other four. The one-digit case is the instructive one: `#fde8e7` against Red-95's `#fce8e7` is indistinguishable on screen and passes visual review, which is why the audit is a grep and not an eye.

## Related

- `~/projects/reference/lailara-design-system/CSS_TOKEN_AUDIT.md` — the canonical rule and procedure
- `~/projects/reference/prevention-rule-scoping.md` — why a governing document belongs next to what it governs
- `app/css/lailara.css` — this project's `:root` block is its token surface
