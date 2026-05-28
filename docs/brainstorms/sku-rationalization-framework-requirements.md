# SKU Rationalization Framework — Requirements

**Status:** Ready for planning
**Date:** 2026-05-28
**Feeds into:** `/ce:plan`

---

## Goal

Build a multi-dimensional SKU rationalization framework that scores every SKU in a brand's portfolio across five dimensions and classifies each into one of four action buckets. V1 ships a polished demo/visualization tool (Cinderhaven 50-SKU data — platform was rebuilt from 90 to 50 SKUs in May 2026), SQL diagnostic queries, and a scoring methodology doc.

**Business question:** Which SKUs should this brand kill, fix, maintain, or double down on — and what does each decision cost or save per year?

---

## Target Audience

**Primary users of the demo:** CEO, COO, VP Sales at specialty food brands $10M–$30M revenue.

**Secondary users:** CFO (validates the financial logic), brokers (need the kill-list math for buyer conversations), retail buyers (actually prefer tighter assortments — the demo is also a vendor communication tool).

**Consulting conversion path:** Demo builds credibility → drives inbound → converts to $15K–$25K SKU Portfolio Audit engagement.

---

## Problem

SKU proliferation silently destroys margin at $10M–$30M specialty food brands. Slotting fees, trade spend, production changeovers, warehouse carrying cost, and data maintenance all accumulate per SKU — but nobody totals them up. The result: the CEO asks "should we cut any SKUs?", nobody can quantify the cost of keeping the underperformers, and nothing gets killed.

The specific gap: CFOs can produce revenue by SKU but not **full loaded contribution by SKU** (after slotting amortization, trade spend, chargebacks, freight, production complexity overhead). Without that number, the keep/kill decision is opinion, not analysis.

---

## The Framework

### Five scoring dimensions (each scored 1–5)

| Dimension | What it measures | Data source |
|---|---|---|
| **Velocity** | Units/store/week vs. category and retailer threshold | Retailer POS data / broker velocity reports |
| **Contribution margin** | Per-unit margin after ALL loaded costs (COGS + slotting amortized + trade spend + chargebacks + freight) | ERP + deduction crosswalk |
| **Shelf-space cost** | Annual cost to maintain this SKU on shelf per retailer (slotting amortization + trade spend + data maintenance + broker time) | Calculated from retailer cost data |
| **Production complexity** | Changeover time, minimum run size, ingredient sourcing difficulty, co-packer capacity consumed | Co-packer data + production schedule |
| **Cannibalization risk** | Does this SKU measurably reduce velocity of a higher-margin sibling? | Cross-elasticity analysis from POS data |

**Scoring:** Each dimension scored 1–5. Weights are user-configurable via the demo tool's UI, defaulting to equal (20% each). The JSON snapshot stores per-dimension scores separately; the weighted composite and quadrant assignment are computed in the browser. Thresholds for 1–5 scoring are calibrated against actual Cinderhaven percentile distributions (p10/p25/p50/p75/p90), not set by intuition.

**Strategic value override:** A qualitative flag (not a scored dimension) that a CEO can set to explicitly retain a failing SKU for non-financial reasons (brand hero, seasonal anchor, line entry point). The framework surfaces the financial cost of that decision explicitly — it doesn't hide it.

### Four-quadrant output

| Quadrant | Criteria | Action |
|---|---|---|
| **Double down** | High velocity, high margin, low cost, no cannibalization | Invest: more shelf space, more promos, production priority |
| **Maintain** | Adequate across dimensions, no red flags | Keep as-is, monitor quarterly |
| **Fix or kill** | Fails one dimension badly, fixable root cause identified | Specific fix with 90-day timeline; delist if not fixed |
| **Kill** | Fails two or more dimensions, no fix available | Delist. Quantify annual savings. Reallocate to "double down" SKUs. |

---

## Cannibalization Methodology

Show both methods, clearly labeled. Rigorous is the headline; proxy is the fallback.

**Rigorous (preferred when data supports it):** Difference-in-differences at the store level — compare velocity of the parent SKU in stores that carried the variant vs. stores that didn't, controlling for time period and seasonality. Requires store-level POS data with sufficient temporal depth and tracked variant launch dates.

**Proxy (fallback):** Did the parent SKU's velocity decline in the quarter the variant launched? Simpler, less defensible, but transparent. Methodology notes must acknowledge the limitation.

Data feasibility must be confirmed via spike (Task 0a in PLAN.md) before building `int_cannibalization_pairs`.

---

## V1 Deliverables

### 1. Demo/visualization tool
- Cinderhaven 90-SKU portfolio, all 90 SKUs scored
- Four-quadrant scatter plot (velocity vs. margin, colored by recommendation)
- Kill list view — each "Kill" SKU with quantified annual loaded cost above contribution
- Cannibalization view — rigorous and/or proxy results, clearly labeled with methodology
- Strategic value override visible where applied
- Lailara Design System v2 throughout: Canvas background (`#f5f3ee`), Chicago navy (`#1f2e7a`), HK teal sequential palette, Playfair Display + Source Sans 3
- Hosted at a public URL; no local-only builds
- Cross-linked from the Velocity Decision Tool portfolio page

### 2. SQL diagnostic queries
- One query per scoring dimension: velocity ranking, loaded contribution by SKU, shelf-space cost calculation, cannibalization detection (both methods)
- Runnable against the Cinderhaven Data Platform (Postgres)
- Stored in `sql/` directory, linked from repo README and demo tool footer

### 3. Scoring methodology doc
- How each dimension is defined, scored, and weighted
- Data sources required for each dimension
- Cannibalization method comparison — rigorous vs. proxy, when to use each
- Strategic value override: what it is, when to apply it, how to quantify the cost
- Stored in `docs/methodology.md`, linked from demo tool

---

## Architecture

### Data flow
```
Cinderhaven platform (Postgres)
  → dbt models (int_loaded_contribution_by_sku,
                int_shelf_space_cost_by_sku,
                int_cannibalization_pairs)
  → Python scoring engine (runs locally)
  → Static scored snapshot (JSON or CSV, committed to repo)
  → Demo tool reads static file (no live DB connection)
  → Hosted at public URL
```

The demo tool does **not** query Postgres directly. It reads from the static snapshot. This makes hosting simple (no runtime database dependency) and keeps sensitive cost data out of the public app.

### dbt models
Three new models go in the **Cinderhaven platform repo** (not this repo). They serve multiple downstream consumers (this framework, "Where the Money Actually Comes From," future analyses).

- `int_loaded_contribution_by_sku` — per-SKU margin after all loaded costs
- `int_shelf_space_cost_by_sku` — annual cost to maintain per retailer
- `int_cannibalization_pairs` — cross-elasticity pairs (method determined by spike)

### Demo tool choice
Static HTML + Plotly.js is preferred over Streamlit for visual quality and full Lailara design system control. Decision must be logged in `DECISIONS.md` before the scoring engine is built (output format depends on it).

---

## Success Criteria

- Scoring engine produces correct quadrant assignments for all 50 Cinderhaven SKUs (verified against hand-built test fixtures for ≥10 SKUs)
- Demo tool is accessible at a stable public URL
- Demo tool passes visual review against Lailara design system (colors, fonts, chart rules)
- Cannibalization view is clearly labeled with which method was used and its limitations
- SQL queries execute successfully against the Cinderhaven platform
- Methodology doc covers all five dimensions and both cannibalization methods

---

## Open Decisions (resolve before or during planning)

| Decision | Options | Blocker for |
|---|---|---|
| Cannibalization data feasibility | Rigorous / proxy / both (spike required) | `int_cannibalization_pairs` dbt model |
| Demo tool choice | Static HTML + Plotly.js / Streamlit | Scoring engine output format |
| Scoring thresholds | To be set against Cinderhaven data distribution | Quadrant assignment logic |

---

## Out of Scope (V1)

- Excel financial model — deferred, potential paid engagement deliverable
- Case study HTML + PDF — deferred, decision pending
- Upload-your-own-data interactivity — v2
- New product launch recommendations
- Retailer-by-retailer assortment optimization
- Pricing optimization
- Delisting execution or buyer conversation management

---

## Dependencies

- **Cinderhaven Data Platform** (Postgres) — must be accessible locally to run dbt models and scoring engine. Already built.
- **Velocity Decision Tool portfolio page** — needs a cross-link added after the demo tool ships.
- **Hosting** — GitHub Pages / Netlify (static HTML) or Streamlit Community Cloud, depending on tool choice.
