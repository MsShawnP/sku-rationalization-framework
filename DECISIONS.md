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

### 2026-05-28 — Use proxy method for cannibalization scoring (rigorous DiD not feasible)
- **Decision:** Build `int_cannibalization_pairs` using the proxy method — cross-sectional velocity comparison between stores carrying a parent+sibling SKU pair vs stores carrying the parent alone. Do not attempt difference-in-differences.
- **Why:** Feasibility spike confirmed DiD is not supported by the Cinderhaven data. All SKUs were authorized within a 6-month window (2024-01-01 to 2024-06-29), so there is no meaningful "pre-variant" temporal window. The ≥4 quarters pre-launch depth required for valid DiD does not exist. The proxy method — comparing parent velocity in stores with vs without a similar sibling SKU — is feasible with the current data structure (store-level scan_data + distribution_log).
- **Scope:** `int_cannibalization_pairs` dbt model; cannibalization scorer in scoring engine; methodology doc
- **Do not:** Label the proxy results as DiD or cross-elasticity analysis. Methodology notes must state that this is a cross-sectional proxy, not a causal estimate, and acknowledge the limitation explicitly.

---

## Visualization

### 2026-05-28 — Demo tool: static HTML + Plotly.js
- **Decision:** Build the demo/visualization tool as a single static HTML file with Plotly.js. Deploy to GitHub Pages.
- **Why:** Visual quality is the stated V1 priority. Static HTML gives full control over Lailara Design System tokens (Canvas background, Chicago/HK palette, Playfair Display + Source Sans 3 typography) without Streamlit's CSS override limitations. No runtime database dependency — the tool reads from the committed JSON snapshot. GitHub Pages hosting is free, instant to deploy, and produces a stable public URL. Streamlit would require Community Cloud and would cap visual customization.
- **Scope:** `app/index.html`, `app/js/visualizations.js`, `app/css/lailara.css`
- **Do not:** Add a live database connection to the demo tool. All data comes from the committed static JSON snapshot.

---

## Output Formats

### 2026-05-28 — Scored output as static JSON snapshot committed to repo
- **Decision:** The Python scoring engine writes `data/cinderhaven_scored.json` to the repo. The demo tool reads this file directly. No live Postgres connection from the demo.
- **Why:** Allows public hosting without exposing the Cinderhaven Postgres instance. Decouples scoring cadence from demo availability. Keeps the demo deployable on static hosting (GitHub Pages, Netlify).
- **Scope:** `run_scoring.py`, `data/cinderhaven_scored.json`, `app/index.html`
- **Do not:** Embed the raw Postgres credentials anywhere in the repo or the deployed demo asset.

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
