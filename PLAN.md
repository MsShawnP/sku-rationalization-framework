# SKU Rationalization Framework — Current Work Plan

The current arc of work. Updated when the arc changes, not every
session. For session-by-session state, see HANDOFF.md.

---

## Goal — 2026-05-28

Ship a multi-dimensional SKU rationalization framework: a polished demo/visualization tool (Cinderhaven 90-SKU data), SQL diagnostic queries, and a scoring methodology doc.

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
- [ ] Query Cinderhaven platform for store-level velocity with variant launch dates
- [ ] Determine: does the data support rigorous cross-elasticity (store-level, pre/post variant launch, controlled for seasonality)?
- [ ] Decision: rigorous method, proxy method, or both? Log outcome in DECISIONS.md before building `int_cannibalization_pairs`

### 0b. Architecture decision: demo tool choice
- [ ] Evaluate static HTML + Plotly.js vs. Streamlit for visual quality and Lailara design system fit
- [ ] Log decision in DECISIONS.md
- [ ] Confirm data output format for scoring engine (JSON or CSV snapshot)

### 1. Data layer (Cinderhaven platform repo — prerequisite)
- [ ] Add `int_loaded_contribution_by_sku` dbt model to Cinderhaven platform
- [ ] Add `int_shelf_space_cost_by_sku` dbt model to Cinderhaven platform
- [ ] Add `int_cannibalization_pairs` dbt model to Cinderhaven platform (method determined by spike in 0a)

### 2. Scoring engine
- [ ] Define 10 test SKUs with hand-verified expected quadrant assignments (test fixtures first)
- [ ] Implement 5-dimension scoring matrix (velocity, contribution margin, shelf-space cost, production complexity, cannibalization risk), each scored 1–5
- [ ] Implement quadrant assignment logic (double down / maintain / fix or kill / kill)
- [ ] Produce scored output for all 90 Cinderhaven SKUs
- [ ] Export scored output as static JSON/CSV snapshot for demo tool
- [ ] Tests: verify quadrant assignments match expected results for test fixtures

### 3. Demo/visualization tool
- [ ] Build in chosen tool (format confirmed in 0b)
- [ ] Four-quadrant scatter plot (velocity vs margin, colored by recommendation)
- [ ] Kill list view with quantified annual savings per SKU
- [ ] Cannibalization view — rigorous and/or proxy methods, clearly labeled
- [ ] Lailara design system applied throughout
- [ ] Deploy to public URL

### 4. SQL diagnostic queries + methodology doc
- [ ] SQL queries for each scoring dimension (velocity ranking, loaded contribution, shelf-space cost, cannibalization detection)
- [ ] Methodology doc: how each dimension is scored and weighted, data sources, cannibalization method and its limitations
- [ ] Link from demo tool footer and repo README

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

- [ ] Cannibalization data feasibility confirmed (spike complete, decision logged)
- [ ] Demo tool choice logged in DECISIONS.md
- [ ] Scoring engine produces correct quadrant assignments for all 90 Cinderhaven SKUs
- [ ] Demo tool is visually polished (Lailara design system), shows scatter plot + kill list + cannibalization analysis
- [ ] Demo tool is accessible at a public URL (no local-only builds)
- [ ] SQL queries runnable against Cinderhaven platform
- [ ] Methodology doc in repo, linked from demo tool
- [ ] Demo tool cross-linked from Velocity Decision Tool portfolio page

---

## Arc history

### 2026-05-28 — Heavy-tier workflow complete (pending v1.0 tag)
- Outcome: /ce:review (18 findings, LEFT JOIN architecture, SQL threshold fix, font self-hosting), /qa (all interactions pass, zero errors), /ce:compound (logic-error solution doc written)
- Next: git tag v1.0, cross-link from Velocity Decision Tool (deferred)

### 2026-05-28 — V1 implementation
- Outcome: U1–U7 complete — calibration, scoring engine, demo tool, SQL queries, methodology doc
- Live: https://msshawnp.github.io/sku-rationalization-framework/app/

### 2026-05-28 — Foundation
- Outcome: Repo scaffolded, state files created, GitHub remote created, /clarify + gates complete
- Tag: v0.1-foundation

---

## Improvement history

<!-- Entries are added by /improve — don't delete this section -->
