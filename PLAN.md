# SKU Rationalization Framework — Current Work Plan

The current arc of work. Updated when the arc changes, not every
session. For session-by-session state, see HANDOFF.md.

---

## Goal — 2026-05-28

Ship a multi-dimensional SKU rationalization framework: a polished demo/visualization tool (Cinderhaven 50-SKU data), SQL diagnostic queries, and a scoring methodology doc.

## Why this arc, why now

Expands the most-asked-about module in the Velocity Decision Tool into a standalone framework. Highest-leverage margin play at $10M–$30M and the clearest foot-in-the-door consulting offer in the portfolio ($15K–$25K SKU Portfolio Audit).

## Business question this arc answers

Which SKUs should this brand kill, fix, maintain, or double down on — and what does each decision cost or save per year?

## Architecture decisions (resolve before building)

**Data portability:** The demo tool is publicly hosted but the Cinderhaven platform is local/self-hosted Postgres. The demo tool reads from a static scored snapshot (JSON or CSV), not a live query. Workflow: run dbt models + scoring engine locally → export scored output → commit to repo → demo tool reads static file.

**Demo tool:** Decide between static HTML + Plotly.js (higher visual quality, full Lailara design system control, hosted on GitHub Pages/Netlify) vs. Streamlit (faster build, limited CSS control). Visual quality is the stated priority — lean static HTML. Log decision in DECISIONS.md before Task 1.

## Tasks

Work in vertical slices — one deliverable end-to-end before moving to the next.

### 0a. Spike: cannibalization data feasibility (one session)
- [x] Query Cinderhaven platform for store-level velocity with variant launch dates
- [x] Determine: does the data support rigorous cross-elasticity (store-level, pre/post variant launch, controlled for seasonality)?
- [x] Decision: rigorous method, proxy method, or both? Log outcome in DECISIONS.md before building `int_cannibalization_pairs`

### 0b. Architecture decision: demo tool choice
- [x] Evaluate static HTML + Plotly.js vs. Streamlit for visual quality and Lailara design system fit
- [x] Log decision in DECISIONS.md
- [x] Confirm data output format for scoring engine (JSON or CSV snapshot)

### 1. Data layer (Cinderhaven platform repo — prerequisite)
- [x] Add `int_loaded_contribution_by_sku` dbt model to Cinderhaven platform
- [x] Add `int_shelf_space_cost_by_sku` dbt model to Cinderhaven platform
- [x] Add `int_cannibalization_pairs` dbt model to Cinderhaven platform (method determined by spike in 0a)

### 2. Scoring engine
- [x] Define 10 test SKUs with hand-verified expected quadrant assignments (test fixtures first)
- [x] Implement 5-dimension scoring matrix (velocity, contribution margin, shelf-space cost, production complexity, cannibalization risk), each scored 1–5
- [x] Implement quadrant assignment logic (double down / maintain / fix or kill / kill)
- [x] Produce scored output for all 50 Cinderhaven SKUs
- [x] Export scored output as static JSON/CSV snapshot for demo tool
- [x] Tests: verify quadrant assignments match expected results for test fixtures

### 3. Demo/visualization tool
- [x] Build in chosen tool (static HTML + Plotly.js)
- [x] Five dimension bar charts, bucket filter, weighted composite ranking
- [x] Click-to-pin detail card with per-dimension scores
- [x] Lailara design system applied throughout
- [x] Deploy to public URL (GitHub Pages)

### 4. SQL diagnostic queries + methodology doc
- [x] SQL queries for each scoring dimension (velocity ranking, loaded contribution, shelf-space cost, cannibalization detection)
- [x] Methodology doc: how each dimension is scored and weighted, data sources, cannibalization method and its limitations
- [x] Link from demo tool footer and repo README

## Out of scope for this arc

- Excel financial model (deferred — potential engagement deliverable)
- Case study HTML + PDF report (deferred — decision pending)
- Upload-your-own-data interactivity (v2)
- New product launch recommendations
- Retailer-by-retailer assortment optimization
- Pricing optimization
- Delisting execution support

## Entry point

The demo tool is hosted as a standalone public URL (GitHub Pages, Netlify, or Streamlit Community Cloud depending on tool choice) and cross-linked from the Velocity Decision Tool portfolio page. SQL queries and methodology doc are in the repo README, linked from the demo tool footer.

## Definition of done for this arc

- [x] Cannibalization data feasibility confirmed (spike complete, decision logged)
- [x] Demo tool choice logged in DECISIONS.md
- [x] Scoring engine produces correct quadrant assignments for all 50 Cinderhaven SKUs
- [x] Demo tool is visually polished (Lailara design system), shows dimension charts + bucket filter + detail card
- [x] Demo tool is accessible at a public URL (GitHub Pages)
- [x] SQL queries runnable against Cinderhaven platform
- [x] Methodology doc in repo, linked from demo tool
- [ ] Demo tool cross-linked from Velocity Decision Tool portfolio page (deferred)

---

## Arc history

### 2026-05-28 — Code review, CSS audit, compound (arc complete)
- Outcome: `/ce:review` 9 findings resolved (debounce, empty states, CSS tokens, chart colors). Full CSS token audit — 5 deviations corrected against `LAILARA_DESIGN_SYSTEM.md`. `/ce:compound` solution doc: `docs/solutions/conventions/css-design-token-drift-2026-05-28.md`. All pushed.
- Deferred (1 item): cross-link demo from Velocity Decision Tool portfolio page

### 2026-05-28 — Heavy-tier workflow complete (pending v1.0 tag)
- Outcome: /ce:review (18 findings, LEFT JOIN architecture, SQL threshold fix, font self-hosting), /qa (all interactions pass, zero errors), /ce:compound (logic-error solution doc written)
- Next: git tag v1.0, cross-link from Velocity Decision Tool (deferred)

### 2026-05-28 — V1 implementation
- Outcome: U1–U7 complete — calibration, scoring engine, demo tool, SQL queries, methodology doc
- Live: https://sku.lailarallc.com

### 2026-05-28 — Foundation
- Outcome: Repo scaffolded, state files created, GitHub remote created, /clarify + gates complete
- Tag: v0.1-foundation

---

## Improvement history

<!-- Entries are added by /improve — don't delete this section -->

### 2026-06-01 — Improvement pass (first post-v1.0 audit)
- **Trigger:** User-initiated — first /improve session after v1.0 release
- **What was reviewed:** Code quality, tests, dependencies, documentation, security, git hygiene
- **What was fixed:**
  - Created `requirements.txt` with pinned versions (psycopg2-binary, pytest)
  - Updated README test count (54 → 80), pip install instruction to use requirements.txt
  - Marked all PLAN.md tasks complete; updated Definition of Done to reflect actual V1 deliverables
  - Extracted shared `src/scoring/db.py` module (load_env + connect); removed duplication from run_scoring.py and calibrate.py; improved POSTGRES_PASSWORD error message
  - Added `TestScoreSkuJsonOutputContract` (6 tests) validating value types and JSON serializability
  - Added `esc()` helper to app.js; applied to all data-derived innerHTML insertions
  - Added SRI hash to Plotly CDN script tag in index.html
  - Moved portfolio brief from root to `docs/`; updated CLAUDE.md reference
  - Added `*.pem`, `*.token`, `token.*` to .gitignore
  - Fixed CLAUDE.md stack section (was "TBD")
- **Deferred:** Nothing — all Critical, Important, and Nice-to-Have items resolved
- **Next review:** 2026-07-01

### 2026-06-29 — Live-site audit (user-initiated, 4 findings)
- **Trigger:** User audited https://sku.lailarallc.com against the repo and filed 4 findings
- **What was reviewed:** Data consistency (quadrant counts), navigation (methodology link), typography (font weights), documentation (test counts)
- **What was fixed:**
  - Stale quadrant counts in README.md, HANDOFF.md, test_canonical_regression.py — all now match source of truth (19 kill, 14 fix_or_kill, 16 maintain, 1 double_down)
  - Rewrote 3 cannibalization threshold tests in test_dimensions.py to match recalibrated CANNIBAL_P50=0.0 (net: 37 tests, was 38)
  - Added methodology footer link in index.html pointing to docs/scoring_methodology.md
  - Replaced static single-weight font files with Google Fonts variable woff2 (Playfair Display v40, Source Sans 3 v19) — eliminates faux-bold
  - Updated README test count to 92 with correct per-file breakdown
  - CSS token audit: all :root tokens and inline Plotly hex values verified against Lailara Design System v2 — no deviations
- **Deferred:** Nothing
- **Next review:** 2026-07-29
