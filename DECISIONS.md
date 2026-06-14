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

### 2026-05-28 — Fix or Kill color: Singapore-55 (#ee8a2a)
- **Why:** Dark teal (HK-15) was visually indistinguishable from the other teal quadrant colors and didn't signal caution. Singapore-55 is the Lailara design system's official warning color — used for warn status in conditional formatting and warning callout borders.
- **Scope:** All Fix or Kill UI elements: quadrant card, badge, bucket filter button, bar chart color
- **Do not:** Use any HK teal for Fix or Kill. Do not use an ad-hoc orange hex — always trace to Singapore family steps.

### 2026-05-28 — Dimension view: 5 scrollable bar charts, not scatter
- **Decision:** Show one horizontal bar chart per dimension, all SKUs ranked on that single dimension, stacked vertically and scrollable. No scatter or two-axis chart.
- **Why:** Scatter plots require data literacy to interpret axes and quadrant positions. Five separate bar charts answer one question each — "how does this SKU rank on velocity?" — without requiring explanation. Built for non-data-scientist clients.
- **Scope:** `app/index.html`, `app/js/app.js` dimension charts section
- **Do not:** Revert to scatter or add a second axis to these charts. Each chart must answer exactly one dimension question.

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

## Consulting & Positioning

### 2026-05-28 — Do not disclose pricing in public-facing README or demo
- **Decision:** Remove the $15K–$25K price point from README.md and any GitHub Pages–hosted content.
- **Why:** The repo is public. Publishing pricing on GitHub invites price anchoring, competitor visibility, and awkward client conversations before discovery.
- **Scope:** README.md, app/index.html footer, any future case study pages
- **Do not:** Add pricing back to any file that ships to GitHub Pages. Pricing belongs in proposals and private collateral only.

### 2026-05-28 — Score all 50 SKUs; surface missing-data SKUs as "insufficient_data" quadrant
- **Decision:** Convert all INNER JOINs in `run_scoring.py` to LEFT JOINs, drive from `raw.product_master` as the spine. SKUs missing any scored dimension (velocity, margin, shelf cost, complexity) are classified as `"insufficient_data"` rather than silently dropped.
- **Why:** The original INNER JOIN approach silently excluded ~40 of 90 SKUs. A portfolio audit must account for every SKU in the portfolio — the missing SKUs may be the hardest cases (newly launched, thin scan data, missing cost records). Dropping them understates or overstates the kill list depending on their composition. `"insufficient_data"` surfaces the data gap explicitly so an analyst can investigate rather than trusting an incomplete picture. Cannibalization risk of None is still treated as 0.0 (no signal ≠ missing data — a different category).
- **Scope:** `run_scoring.py` (query), `src/scoring/dimensions.py` (all 4 non-cannibalization scoring functions), `src/scoring/engine.py` (signature), `src/scoring/quadrants.py` (assign_quadrant, compute_weighted_score)
- **Do not:** Treat `cannibalization_risk=None` as missing data — it means fewer than 3 solo stores, which is absence of a cannibalization signal, not a data gap.

---

## Design System

### 2026-05-28 — CSS token audit is a mandatory pre-milestone step for all Lailara projects
- **Decision:** Before every milestone commit (version tags, PRs touching CSS), grep all hex values in CSS files and verify each against the authoritative `LAILARA_DESIGN_SYSTEM.md`. All hex values must live only in `:root`; every `:root` token must trace to a named design system step.
- **Why:** Five deviations accumulated in `lailara.css` during V1 authoring without an audit pass. Two involved off-by-1-to-3 digit hex values (`#e5e8f5` vs `#e8eaf4`, `#fde8e7` vs `#fce8e7`) that are invisible on screen but wrong in print and against the spec. One was an invented token (`--canvas-hover`) with no design system backing. None were caught until the `/ce:review` pass.
- **Scope:** All projects using the Lailara design system; any session that writes or extends CSS rule bodies.
- **Do not:** Write hex values directly in rule bodies, even if the value appears correct. Only `:root` token definitions may contain hex literals.

---

## Process & Workflow

### 2026-06-01 — Verify agent-flagged critical findings before presenting them as critical
- **Decision:** Before surfacing any agent finding as Critical or High severity, manually verify it against the actual code.
- **Why:** A security audit agent flagged a `.env` path disagreement as critical. Manual verification showed both paths resolved identically — the difference in ancestor count was correct given the scripts' different directory depths. Presenting an unverified agent finding as "Critical" erodes trust in the audit process.
- **Scope:** All sessions using automated review agents (`/ce:review`, `/security-review`, custom audit agents). Global.
- **Do not:** Present agent-flagged Critical/High findings to the user without first checking them manually against the actual code.

---

## Reversed / Superseded

[Nothing yet]
