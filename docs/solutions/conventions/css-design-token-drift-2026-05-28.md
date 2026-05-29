---
title: CSS design token drift in Lailara projects
date: 2026-05-28
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

## Context

Lailara projects use a design system with named color families (Chicago, Hong Kong, Singapore,
Tokyo, New York) mapped to specific hex values. Each project CSS file defines a `:root` block
with custom properties corresponding to those named steps. When a developer writes a hex value
anywhere outside that `:root` block — or invents a token name that doesn't trace to a design
system step — the project silently drifts from the canonical palette.

During V1 implementation of the SKU Rationalization demo tool, `app/css/lailara.css` was
authored directly without a design system audit pass (session history). Hex values were used by
value rather than by name. Over the course of development and code review, five deviations
accumulated:

1. An invented token (`--canvas-hover: #faf9f6`) with no corresponding design system step
2. Badge background values off by 1–3 hex digits (`#e5e8f5` vs Chicago-95 `#e8eaf4`; `#fde8e7`
   vs Red-95 `#fce8e7`)
3. An `rgba()` expression in a rule body duplicating an existing `:root` token (`--card-border`)
4. A print media shorthand (`#333`) instead of `var(--text-primary)`
5. A mobile `border-radius` of `4px` exceeding the 2px design system cap

The `/ce:review` pass surfaced the most visible case first: an amber `#c87e0d` that was not in
the canonical palette at all. A subsequent full audit against `LAILARA_DESIGN_SYSTEM.md` found
the remaining four. Drift is dangerous in this system because the deviations are visually
indistinguishable — a value 1–3 hex digits wrong looks correct on screen but is wrong in print
and against the spec.

## Guidance

### The rule: all color values live only in `:root`

Every hex value and `rgba()` expression in a project CSS file must appear exactly once: inside
the `:root` custom properties block. Rule bodies use only `var()` references. Token names must
correspond to a named step in the Lailara design system.

```css
/* Correct: :root only, name matches design system step */
:root {
  --chicago-95: #e8eaf4;                    /* Chicago-95 — table row hover */
  --red-95:     #fce8e7;                    /* Red-95 — error/kill badge surface */
  --card-border: rgba(255, 255, 255, 0.12); /* Card border token */
}

/* Rule bodies reference tokens only — no inline hex */
.badge--maintain    { background: var(--chicago-95); }
.badge--kill        { background: var(--red-95); }
.dim-row__bar-track { border-color: var(--card-border); }
```

### The audit procedure

Run before every milestone commit or PR touching CSS:

1. **Read the authoritative source.** Open `LAILARA_DESIGN_SYSTEM.md` in the published design
   system repo. Use the CSS custom properties block as the canonical token list. Do not rely on
   CLAUDE.md summaries, which may lag.

2. **Grep for all hex values in CSS files.**
   Pattern: `#[0-9a-fA-F]{3,8}` across `*.css`.

3. **Check every hit.** Any match outside the `:root` block is a violation. Any match inside
   `:root` whose name doesn't correspond to a design system step is a violation.

4. **Cross-reference values.** For every `:root` token, verify its hex against the design
   system's definition. A token named `--chicago-95` must be `#e8eaf4`, not `#e5e8f5`.

5. **Fix violations** by moving the value to `:root` with the correct name and hex, then
   replacing all usages with `var(--token-name)`.

6. **Verify the fix loaded.** Browser caches may serve the old stylesheet. Force a fresh fetch:

```html
<!-- Append version query string after editing CSS -->
<link rel="stylesheet" href="css/lailara.css?v=20260528">
```

Confirm corrected values with `getComputedStyle(document.documentElement).getPropertyValue('--token-name')` before closing verification.

## Why This Matters

**Small deviations are invisible until they matter.** A badge background of `#e5e8f5` instead
of `#e8eaf4` passes visual review. A kill-state background of `#fde8e7` instead of `#fce8e7` is
indistinguishable at normal screen brightness. These errors surface in print, in high-fidelity
client mockups, or in precise color comparisons — at the worst possible moment.

**Invented tokens break the system.** A token like `--canvas-hover: #faf9f6` looks like a
design system token but isn't one. It establishes an undocumented dependency, produces a
different color than the spec intends, and will mislead future developers — including future
Claude sessions — who assume every `:root` token is canonical.

**Inline duplicates create maintenance debt.** When `rgba(255,255,255,0.12)` appears both in
`:root` as `--card-border` and hardcoded in a rule body, the two can diverge independently: the
`:root` token is updated, the inline is forgotten. No error appears; the component silently
renders a different color.

**The audit is cheap; the drift is expensive.** A grep takes seconds. Correcting undocumented
drift after a client deliverable has shipped is a much larger problem.

## When to Apply

- Before any milestone commit (v1.0, v1.1, release tags)
- Before creating a PR for design or CSS changes
- After any session where new CSS rule bodies were authored
- When adding a new component to an existing Lailara project
- When a design system update is published — re-audit all active projects against new token
  definitions

The audit is also worth running at session start on any project whose CSS was last touched by a
different session.

## Examples

### Violation 1 — Invented token, wrong role

```css
/* WRONG: name has no design system step; value is a guessed near-white */
:root {
  --canvas-hover: #faf9f6;
}
table tr:hover { background: var(--canvas-hover); }
```

```css
/* CORRECT: Chicago-95 is the specified table row hover color */
:root {
  --chicago-95: #e8eaf4;   /* Chicago-95 */
}
table tr:hover { background: var(--chicago-95); }
```

---

### Violation 2 — Value 3 digits wrong (visually similar, spec-wrong)

```css
/* WRONG: #e5e8f5 is not a design system step */
.badge--maintain { background: #e5e8f5; }
```

```css
/* CORRECT: Chicago-95 is #e8eaf4 */
:root {
  --chicago-95: #e8eaf4;   /* Chicago-95 */
}
.badge--maintain { background: var(--chicago-95); }
```

---

### Violation 3 — Value 1 digit wrong (impossible to spot visually)

```css
/* WRONG: #fde8e7 looks like Red-95 but is not */
.badge--kill  { background: #fde8e7; }
.load-error   { background: #fde8e7; }
```

```css
/* CORRECT: Red-95 is #fce8e7 */
:root {
  --red-95: #fce8e7;   /* Red-95 */
}
.badge--kill  { background: var(--red-95); }
.load-error   { background: var(--red-95); }
```

---

### Violation 4 — Inline duplicate of an existing `:root` token

```css
/* WRONG: --card-border is defined in :root; inline bypasses it and can diverge */
.dim-row__bar-track {
  border-color: rgba(255, 255, 255, 0.12);
}
```

```css
/* CORRECT: reference the token that already exists */
:root {
  --card-border: rgba(255, 255, 255, 0.12);   /* Card border */
}
.dim-row__bar-track {
  border-color: var(--card-border);
}
```

---

### Cache busting after a CSS edit

```javascript
// Verify corrected token values loaded — bust cache first
document.querySelector('link[rel="stylesheet"]').href =
  '/app/css/lailara.css?v=' + Date.now();

// Then confirm
getComputedStyle(document.documentElement).getPropertyValue('--chicago-95');
// Expected: " #e8eaf4"
```

## Related

- `LAILARA_DESIGN_SYSTEM.md` — canonical token definitions (published repo at
  `~/projects/published/lailara-design-system/`)
- `app/css/lailara.css` — `:root` block is the project-level token surface
