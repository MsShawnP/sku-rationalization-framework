# SKU Rationalization Framework — Decisions Log

Permanent record of choices that should survive session turnover.
If a decision is reversed, strike it through and add the replacement
below — don't delete.

---

## Format

Each entry:
- **Date** — when decided
- **Decision** — one sentence, imperative voice
- **Why** — the reasoning, including what was tried and rejected
- **Scope** — what this applies to (file, chunk, deliverable, or "global")
- **Do not** — explicit anti-instructions, if any

---

## Architecture & Pipeline

### 2026-05-28 — Tier set to Heavy
- **Why:** Portfolio piece with a consulting engagement offer attached; expected
  maintenance > 3 months; requires /office-hours, /plan-ceo-review, and
  /plan-eng-review gates before build.
- **Scope:** Global
- **Do not:** Skip gstack gates even when the brief feels detailed enough.

### 2026-05-28 — Stack deferred to /clarify
- **Why:** Stack has a preliminary spec in the project brief (Python, Streamlit,
  dbt, Postgres, Plotly, pandas, openpyxl) but the 95% confidence prompt may
  reveal constraints or simplifications.
- **Scope:** Global

---

## Data & Schema

[Decisions about data sources, schemas, transformations]

---

## Visualization

[Chart conventions, palette decisions, interactivity choices]

---

## Output Formats

[Decisions about deliverable formats, structure, organization]

---

## Writing & Voice

### 2026-05-28 — Economist style for all written output
- **Why:** Lailara design system standard; data-forward, no marketing voice.
- **Scope:** Global
- **Do not:** Use hedge words ("may," "might," "could help") when the data
  supports a direct claim.

---

## Reversed / Superseded

[Nothing yet]
