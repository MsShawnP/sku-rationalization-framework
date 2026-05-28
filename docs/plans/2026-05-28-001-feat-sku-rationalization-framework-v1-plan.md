---
title: "feat: SKU Rationalization Framework — V1"
created: 2026-05-28
status: active
origin: docs/brainstorms/sku-rationalization-framework-requirements.md
---

# feat: SKU Rationalization Framework — V1

Build a multi-dimensional SKU scoring framework on top of the Cinderhaven Data Platform and ship it as a polished static demo tool. Scores every SKU on five dimensions, produces a four-quadrant classification, and lets users adjust dimension weights to see how the classification changes.

---

## Problem Frame

Specialty food brands at $10M–$30M accumulate SKUs and never cut them because they can't answer: *"What does it cost to keep this SKU on shelf for a year?"* Revenue by SKU is easy. Full loaded contribution — after slotting amortization, trade spend, chargebacks, freight, and production complexity overhead — is not. Without that number, the keep/kill decision is opinion.

This framework makes that number visible across five dimensions, classifies every SKU into one of four action buckets, and shows which SKUs are eating more than they earn.

**(see origin: `docs/brainstorms/sku-rationalization-framework-requirements.md`)**

---

## Scope Boundaries

### In scope (V1)
- Python scoring engine (5 dimensions, configurable weights, quadrant classification)
- Three new dbt models in the Cinderhaven platform repo (loaded contribution, shelf-space cost, cannibalization pairs)
- Static JSON snapshot of scored Cinderhaven data (50 SKUs)
- Static HTML + Plotly.js demo tool: four-quadrant scatter, kill list, cannibalization view, weight controls
- SQL diagnostic queries (4 files) and methodology doc
- Deployment to public URL (GitHub Pages or Netlify)

### Deferred for later
- Excel financial model — deferred as potential engagement deliverable
- Case study HTML + PDF report — decision pending
- Upload-your-own-data interactivity — V2

### Outside this product's identity
- New product launch recommendations
- Retailer-by-retailer assortment optimization
- Pricing optimization
- Delisting execution / buyer conversation management

### Deferred to follow-up work
- Email-gating the methodology doc or any deliverable
- Embedding the demo in the portfolio site (separate task)
- Cross-link from Velocity Decision Tool (separate task, after demo ships)

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Demo tool | Static HTML + Plotly.js | Full Lailara design system control; no Python runtime dependency for hosting; hosts on GitHub Pages/Netlify |
| Data architecture | Static JSON snapshot; no live DB query from demo | Cinderhaven Postgres is local/self-hosted; public hosting can't reach it |
| Scoring weights | User-configurable via UI; default equal (20% each dimension) | User asked for ability to weight dimensions differently; equal default is simplest starting point |
| Scoring output | Per-dimension scores (1–5) stored in JSON; composite + quadrant computed in JavaScript | Enables live weight recalculation without regenerating the snapshot |
| dbt model location | Cinderhaven platform repo (`models/intermediate/`) | Models serve multiple downstream consumers; SSOT is the platform |
| Cannibalization method | Determined by spike (U1) — prefer rigorous DiD if data supports | `stg_scan_data` has store/week/SKU grain; `fct_distribution.authorized_date` may have launch dates |
| Threshold calibration | Calibration script queries Cinderhaven p10/p25/p50/p75/p90 per dimension | Velocity tool failure mode: intuition-set thresholds were wrong by 5x when dataset changed |
| COGS formula | `units_ordered × case_pack_qty × cogs_per_unit` for B2B; DTC uses `units_ordered` directly | Documented failure in both where-the-money-comes-from and cinderhaven-data-platform: units_ordered is in cases for B2B |
| SKU count | 50 (actual platform state) | Brief says 90, but platform was rebuilt to 50 in May 2026; headline finding recalibrated accordingly |
| Quadrant colors | Double down: Chicago-20 (`#1f2e7a`); Maintain: HK-35 (`#158f75`); Fix or kill: Singapore-55 (`#ee8a2a`); Kill: Tokyo-40 (`#b82d4a`) | Matches Lailara divergent palette logic; positive=HK/Chicago, warning=Singapore, negative=Tokyo |

---

## High-Level Technical Design

*This illustrates the intended approach and is directional guidance for review, not implementation specification.*

### Data flow

```
Cinderhaven Postgres (local)
    dim_products, stg_scan_data, fct_distribution,
    fct_chargebacks, stg_promotions, dim_costs
         │
         ▼ (dbt build — cinderhaven-data-platform repo)
    int_loaded_contribution_by_sku   (U2)
    int_shelf_space_cost_by_sku      (U2)
    int_cannibalization_pairs        (U3)
         │
         ▼ (scripts/calibrate.py — this repo)
    src/scoring/constants.py (thresholds from p10/p25/p50/p75/p90)
         │
         ▼ (scripts/run_scoring.py — this repo)
    Python scoring engine
    → per-dimension scores (1–5) for all 50 SKUs
         │
         ▼
    data/cinderhaven_scored.json  ◄── committed to repo
         │
         ▼ (browser)
    app/index.html + app/js/visualizations.js
    → user adjusts weights → JS computes composite + quadrant
    → Plotly.js renders scatter, kill list, cannibalization view
         │
         ▼
    Public URL (GitHub Pages / Netlify)
```

### JSON snapshot schema (directional)

Each SKU entry carries all 5 dimension scores independently so the browser can recompute the composite for any weight configuration:

```
{
  sku_id, sku_name, product_line,
  dimension_scores: { velocity, contribution_margin, shelf_space_cost,
                      production_complexity, cannibalization_risk },  // each 1–5
  loaded_cost_annual,       // $ — for kill-list savings calculation
  loaded_contribution,      // $ — for net-negative flag
  strategic_value_override, // bool
  strategic_value_note      // string or null
}
```

### Scoring engine architecture

Mirror `calcs.py` from retail-velocity-decision-tool: pure functions, DataFrame in → DataFrame out, no DB access in the scoring module. Each dimension is a separate function. Thresholds live in `constants.py`. Quadrant assignment is separate from scoring, takes a weighted composite as input.

---

## Output Structure

```
sku-rationalization-framework/
├── scripts/
│   ├── calibrate.py              — query Cinderhaven, output p10/p25/p50/p75/p90 per dimension
│   └── run_scoring.py            — full pipeline: connect → score → write data/cinderhaven_scored.json
├── src/
│   └── scoring/
│       ├── __init__.py
│       ├── constants.py          — thresholds dict, default weights, dimension metadata
│       ├── dimensions.py         — velocity_score(), margin_score(), shelf_cost_score(), etc.
│       ├── engine.py             — score_portfolio(df, connection) → scored DataFrame
│       ├── quadrants.py          — assign_quadrant(scores_df, weights) → quadrant column
│       └── cannibalization.py    — detect_pairs(df, method) → pairs DataFrame
├── data/
│   └── cinderhaven_scored.json   — committed static snapshot
├── app/
│   ├── index.html
│   ├── js/
│   │   └── visualizations.js     — scatter, kill list, cannibalization view + weight controls
│   └── css/
│       └── lailara.css           — design tokens
├── sql/
│   ├── velocity_ranking.sql
│   ├── loaded_contribution.sql
│   ├── shelf_space_cost.sql
│   └── cannibalization_detection.sql
├── tests/
│   ├── scoring/
│   │   ├── test_dimensions.py
│   │   ├── test_engine.py
│   │   ├── test_quadrants.py
│   │   └── test_cannibalization.py
│   └── fixtures/
│       └── test_skus.json        — 10+ hand-verified SKUs with expected per-dimension scores
└── docs/
    ├── methodology.md
    ├── brainstorms/
    └── plans/
```

---

## Implementation Units

### U1. Decision spikes: cannibalization feasibility + demo tool confirmation

**Goal:** Run the cannibalization data feasibility spike and confirm the demo tool architecture before any dbt models are written.

**Requirements:** Resolves the two open architecture decisions from the requirements doc before committing to `int_cannibalization_pairs` design.

**Dependencies:** None

**Files:**
- `DECISIONS.md` — two new entries (cannibalization method + demo tool)

**Approach:**
1. Query the Cinderhaven platform: does `fct_distribution.authorized_date` exist per SKU per store? Does `stg_scan_data` have enough temporal depth (≥4 quarters pre- and post-variant launch) for a valid DiD?
2. If rigorous DiD is feasible: proceed with `int_cannibalization_pairs` using store-level DiD design. If not: fall back to proxy (quarter-over-quarter velocity drop at variant launch), or expose both methods.
3. Confirm static HTML + Plotly.js as the demo tool. Log in DECISIONS.md.

**Test expectation:** None — spike produces DECISIONS.md entries, not runnable code.

**Verification:** Both decisions are logged in DECISIONS.md before U2/U3 begin.

---

### U2. dbt models: loaded contribution and shelf-space cost

**⚠️ Target repo: `cinderhaven-data-platform` (`models/intermediate/`) — not this repo.**

**Goal:** Build two new intermediate dbt models that produce per-SKU loaded contribution and annual shelf-space cost.

**Requirements:** Provides the margin and shelf-cost dimensions for the scoring engine.

**Dependencies:** U1 (architecture confirmed)

**Files (cinderhaven-data-platform repo):**
- `models/intermediate/int_loaded_contribution_by_sku.sql`
- `models/intermediate/int_shelf_space_cost_by_sku.sql`
- `models/intermediate/schema.yml` (add both model docs)

**Approach:**

`int_loaded_contribution_by_sku`:
- Start from `mart_channel_contribution.sql` as the reference — deductions, chargebacks, and trade spend assembly pattern is already proven there.
- COGS formula: `SUM(ol.units_ordered × pm.case_pack_qty × sc.cogs_per_unit)` for B2B rows (`ol.channel = 'B2B'`). DTC uses `ol.units_ordered` directly (already in individual units). **This exact formula error has caused a factor-of-15 undercount twice on this codebase.**
- Include: slotting amortized over 24 months (2-year SKU life at mass retail), trade spend from `stg_promotions.promo_cost` per SKU, chargeback rates from `stg_retailer_chargebacks` + `stg_distributor_chargebacks`.
- Output grain: one row per SKU with `loaded_contribution_annual` and `loaded_cost_annual`.

`int_shelf_space_cost_by_sku`:
- Annual cost to maintain a SKU on shelf at each retailer: slotting amortization + trade spend allocation + data maintenance estimate.
- Output grain: one row per SKU per retailer, plus a summary row per SKU across all retailers.

Before writing: query `information_schema.tables` in the live DB to confirm every source table exists. The dbt project structure shows models that were never materialized.

**Patterns to follow:** `mart_channel_contribution.sql`, `stg_retailer_chargebacks`, `stg_distributor_chargebacks`, `stg_promotions` in the Cinderhaven platform.

**Test scenarios:**
- `int_loaded_contribution_by_sku`: no NULLs on `loaded_contribution_annual` or `loaded_cost_annual` for any of the 50 SKUs
- `int_loaded_contribution_by_sku`: a B2B order with `units_ordered=10` and `case_pack_qty=12` and `cogs_per_unit=2.50` produces COGS contribution of `10 × 12 × 2.50 = $300`, not `10 × 2.50 = $25` — verify with a known order row
- `int_shelf_space_cost_by_sku`: every SKU has at least one retailer row; no negative costs
- `dbt parse` validates both models without a live DB connection

**Verification:** `dbt build --select int_loaded_contribution_by_sku int_shelf_space_cost_by_sku` succeeds. Query results spot-checked against a known SKU's cost records.

---

### U3. dbt model: cannibalization pairs

**⚠️ Target repo: `cinderhaven-data-platform` (`models/intermediate/`) — not this repo.**

**Goal:** Build `int_cannibalization_pairs` using the method determined in U1.

**Requirements:** Provides the cannibalization risk dimension for the scoring engine.

**Dependencies:** U1 (method confirmed), U2 (loaded contribution available for filtering pairs by margin direction)

**Files (cinderhaven-data-platform repo):**
- `models/intermediate/int_cannibalization_pairs.sql`
- `models/intermediate/schema.yml` (add model docs)

**Approach:**

**Rigorous path (DiD — if U1 confirms data feasibility):**
- For each variant-parent pair: compare parent SKU velocity in stores that carried the variant vs. stores that didn't, in the same time window post-launch.
- Source: `stg_scan_data (sku, store_id, week_ending, units_sold)` × `fct_distribution.authorized_date` for launch date.
- A pair is flagged as cannibalizing if the treatment effect is negative and statistically meaningful (velocity in variant-carrying stores declined vs. control stores).
- Output: `(cannibalizing_sku, parent_sku, treatment_effect_velocity, method='rigorous')`

**Proxy path (if rigorous is not feasible):**
- For each potential pair: did the parent SKU's quarterly velocity drop by > threshold% in the quarter the variant launched across all stores?
- Source: `stg_scan_data` aggregated to quarterly grain × `fct_distribution` for launch quarter.
- Output: `(cannibalizing_sku, parent_sku, velocity_drop_pct, method='proxy')`

Both methods produce the same output schema. The `method` column carries forward into the scoring engine and the demo tool's cannibalization view.

**Test scenarios:**
- No self-referential pairs (`cannibalizing_sku = parent_sku`)
- Pairs are directional (A cannibalizes B does not imply B cannibalizes A)
- `method` column is populated for every row ('rigorous' or 'proxy')
- SKUs without any variant siblings produce no rows (correct absence)
- Known cannibalizing pair (if one exists in the data) appears in output

**Verification:** Row count is reasonable (not zero, not every SKU pairing). Spot-check known variant families.

---

### U4. Calibration script and scoring constants

**Goal:** Build a calibration script that queries Cinderhaven percentile distributions per dimension and produces the `constants.py` threshold file.

**Requirements:** Sets the scoring thresholds against actual data — not intuition. Velocity tool failure mode: original thresholds were 5x wrong when dataset changed.

**Dependencies:** U2, U3 complete and dbt models materialized

**Files:**
- `scripts/calibrate.py`
- `src/scoring/constants.py` — generated output, then committed

**Approach:**
- `calibrate.py` connects to Cinderhaven Postgres, queries `int_loaded_contribution_by_sku`, `int_shelf_space_cost_by_sku`, `int_cannibalization_pairs`, and a velocity aggregation to compute p10/p25/p50/p75/p90 for each of the five scoring dimensions across all 50 SKUs.
- Prints a Python dict of `THRESHOLDS` and `DEFAULT_WEIGHTS` to stdout. The human reviews and commits the output as `src/scoring/constants.py`.
- `constants.py` also defines dimension metadata (human-readable names, units, data source) and `QUADRANT_THRESHOLDS` (composite score ranges for each bucket — set initially by inspection of the calibration output).

**Test scenarios:**
- `calibrate.py` completes without error when Postgres is reachable
- Output contains all five dimension threshold dicts
- Running calibration twice produces identical output (deterministic)
- `constants.py` is valid Python and importable without error

**Verification:** Run `scripts/calibrate.py` against live platform. Review threshold output. Commit `constants.py`.

---

### U5. Scoring engine

**Goal:** Implement the five-dimension scoring engine as pure Python functions. Score all 50 Cinderhaven SKUs and export the static JSON snapshot.

**Requirements:** Scoring engine, quadrant assignment, JSON export — the core analytical unit.

**Dependencies:** U4 (constants.py and fixtures ready)

**Files:**
- `src/scoring/__init__.py`
- `src/scoring/constants.py` (from U4)
- `src/scoring/dimensions.py`
- `src/scoring/engine.py`
- `src/scoring/quadrants.py`
- `src/scoring/cannibalization.py`
- `scripts/run_scoring.py`
- `data/cinderhaven_scored.json`
- `tests/scoring/test_dimensions.py`
- `tests/scoring/test_engine.py`
- `tests/scoring/test_quadrants.py`
- `tests/scoring/test_cannibalization.py`
- `tests/fixtures/test_skus.json`

**Approach:**

Mirror the `calcs.py` pattern from `retail-velocity-decision-tool` exactly: pure functions, DataFrame in → DataFrame out, no DB access in scoring modules.

`dimensions.py`: One function per dimension. Each takes a row (or Series) and returns an integer 1–5 using breakpoints from `constants.THRESHOLDS`. Example shape: `velocity_score(units_per_store_per_week, retailer) → int`.

`engine.py`: `score_portfolio(df) → df` — applies all five dimension functions, adds `strategic_value_override` column, returns a DataFrame with one row per SKU and columns for each dimension score plus metadata.

`quadrants.py`: `assign_quadrant(scores_df, weights=None) → series` — accepts per-dimension scores and an optional weight dict (defaults to equal weights from `constants.DEFAULT_WEIGHTS`). Computes weighted composite (scale 1–5). Assigns quadrant by composite score and override flag.

`cannibalization.py`: `load_cannibalization_pairs(conn) → df` — reads `int_cannibalization_pairs` from Postgres. `cannibalization_score(sku_id, pairs_df) → int` — returns 1 (high risk) to 5 (no risk) based on whether the SKU appears as a cannibalizing SKU in the pairs table.

`run_scoring.py`: Entry point. Connects to Postgres via environment variable (`DATABASE_URL`), calls `score_portfolio()`, calls `assign_quadrant()` with default weights, serializes to `data/cinderhaven_scored.json` with the schema defined in High-Level Technical Design.

**Build test fixtures first.** Define `tests/fixtures/test_skus.json` with ≥10 SKUs before writing any scoring logic. Each fixture SKU should have hand-verified expected per-dimension scores and expected quadrant. Include at least:
- One clear "Kill" (≥2 dimensions at score 1–2)
- One clear "Double down" (all dimensions ≥4)
- One "Fix or kill" (exactly one bad dimension, clear root cause)
- One "Maintain" (middle scores across the board)
- One SKU with strategic_value_override=true (should stay out of "Kill" regardless of score)
- One SKU affected by cannibalization risk

**Patterns to follow:** `retail-velocity-decision-tool/app/calcs.py` (classify_quadrant, score_span, pure-function pattern), `constants.py` (thresholds dict structure).

**Test scenarios:**
- `velocity_score()`: SKU at p90 velocity → score 5; SKU at p10 → score 1; SKU at median → score 3
- `assign_quadrant()` with default weights: Kill SKU (test fixture) → "Kill"; Double down SKU → "Double down"
- `assign_quadrant()` with velocity weight doubled: a velocity-weak/margin-strong SKU shifts from "Maintain" to "Fix or kill"
- Strategic value override = True: SKU that would otherwise score "Kill" → "Maintain" (override respected)
- `score_portfolio()`: all 50 Cinderhaven SKUs produce a non-NULL score on every dimension
- JSON output: all 50 SKUs present, no missing dimension_scores keys, `loaded_cost_annual` and `loaded_contribution` populated

**Verification:** Run `pytest tests/scoring/` — all tests pass. Run `scripts/run_scoring.py` — `data/cinderhaven_scored.json` written without error, spot-check 5 SKUs against expected values.

---

### U6. Static demo tool

**Goal:** Build the demo/visualization tool as a static HTML + Plotly.js app reading from `data/cinderhaven_scored.json`. Deploy to a public URL.

**Requirements:** The portfolio-facing deliverable. Visual quality is the primary criterion.

**Dependencies:** U5 (`data/cinderhaven_scored.json` committed)

**Files:**
- `app/index.html`
- `app/js/visualizations.js`
- `app/css/lailara.css`

**Approach:**

**Design tokens** — Use the Lailara Design System v2 (see parent `CLAUDE.md`). Key tokens:
- Background: Canvas `#f5f3ee` — non-negotiable, the brand signature
- Quadrant colors: Chicago-20 `#1f2e7a` (Double down), HK-35 `#158f75` (Maintain), Singapore-55 `#ee8a2a` (Fix or kill), Tokyo-40 `#b82d4a` (Kill)
- Text: London-20 `#333333` body, London-35 `#595959` labels/axes, London-5 `#0d0d0d` chart titles
- Gridlines: London-85 `#d9d9d9`, horizontal only
- Fonts: Playfair Display (chart titles, headline numbers) + Source Sans 3 (everything else) — self-host woff2, no Google Fonts CDN
- Content max-width: 900px; border-radius: 2px everywhere

**Three views:**

*Four-quadrant scatter:*
- X axis: velocity score (1–5). Y axis: contribution margin score (1–5).
- Each dot is one SKU, colored by quadrant, sized by `loaded_cost_annual`.
- Quadrant boundary lines at threshold crossings.
- **Critical:** never use Plotly autorange when reference lines are present. Collect all data values and boundary line values, add 10% padding, set `range` explicitly with `autorange: false`. Documented failure mode from the velocity tool.
- Click a dot → pin dark callout card above chart showing all 5 dimension scores, quadrant, loaded cost, and strategic value note. Click again to dismiss. Non-selected dots dim to opacity 0.2.
- Every dot gets a label (SKU name on hover, or adjacent for low-density areas).

*Kill list:*
- Table of "Kill" quadrant SKUs sorted by `loaded_cost_annual - loaded_contribution` descending (most net-negative first).
- Columns: SKU name, product line, net-negative cost/year, each dimension score (1–5), and a one-line root cause note.
- Lailara dark callout card style for the total savings summary line.

*Cannibalization view:*
- Table or network showing cannibalizing pairs.
- Method label ('rigorous' or 'proxy') displayed prominently.
- Methodology limitation note below (footnote style, 11px Source Sans 3 italic).

*Weight controls:*
- Five sliders (one per dimension), default equal (20% each).
- As user moves a slider, JS recomputes weighted composite from per-dimension scores in JSON → reassigns quadrants → re-renders scatter and kill list in real time.
- Weight total normalized to 100% automatically.

**Footnotes:** Every chart section has a footnote: data source (Cinderhaven Data Platform), data date (snapshot date), methodology notes, and a link to `docs/methodology.md`.

**Deployment:** GitHub Pages (preferred — free, no runtime) or Netlify. Confirm `app/` serves as the web root.

**Test scenarios:**
- All 50 SKUs render as dots in the scatter; no blank chart
- Quadrant boundary lines are visible (not clipped by autorange)
- Moving a dimension weight slider reassigns at least one SKU to a different quadrant (verify with a known borderline SKU)
- Kill list contains only "Kill" quadrant SKUs and is sorted correctly
- Cannibalization view shows the method label
- Renders correctly at 900px, 1280px, and 375px (mobile) widths
- Canvas background (`#f5f3ee`) applied to `<body>` and all chart backgrounds
- Chart titles use Playfair Display; axis labels use Source Sans 3

**Test expectation:** Automated tests can cover data binding and weight recalculation logic. Visual Lailara compliance requires manual review — run the app in a browser and verify against the design system before marking done.

**Verification:** Deploy to public URL. Open in browser. Confirm: all 50 SKUs visible, weight sliders work, kill list updates, cannibalization view loads, Canvas background present. Share URL.

---

### U7. SQL diagnostic queries and methodology doc

**Goal:** Write the four SQL diagnostic queries and the methodology doc. Link both from the demo tool and the repo README.

**Requirements:** The SQL queries are the "show your work" artifact for the practice's technical credibility.

**Dependencies:** U2, U3 (models must exist for queries to be valid)

**Files:**
- `sql/velocity_ranking.sql`
- `sql/loaded_contribution.sql`
- `sql/shelf_space_cost.sql`
- `sql/cannibalization_detection.sql`
- `docs/methodology.md`
- `README.md` (update with how-to-run, links to methodology and demo)

**Approach:**

SQL queries read from the Cinderhaven platform's intermediate models. Each query is self-contained and annotated with inline comments explaining methodology decisions (not implementation details — the WHY, per `src/CLAUDE.md` conventions).

`cannibalization_detection.sql`: includes both methods as separate CTEs, labeled, with a method-selection comment at the top.

`docs/methodology.md`:
- Five dimensions: definition, data source, scoring logic (how 1–5 maps to the underlying value), and known limitations
- Cannibalization: rigorous method and proxy method, when to use each, what the method cannot detect
- Weight configuration: what equal weights means, when to adjust, how to interpret results when weights differ
- Strategic value override: definition, when to apply, how to quantify the cost of the override
- Data sources: Cinderhaven Data Platform mart tables; note that data is synthetic

**Test scenarios:**
- All four SQL queries execute without error against the Cinderhaven platform
- `velocity_ranking.sql` returns exactly 50 rows (one per SKU)
- `loaded_contribution.sql` returns positive `loaded_cost_annual` for all rows
- `cannibalization_detection.sql` returns results with a `method` column populated
- `docs/methodology.md` covers all five dimensions, both cannibalization methods, and weight configuration — review against the requirements doc coverage list

**Verification:** Run all four queries against live Cinderhaven platform. Read methodology doc end-to-end — confirm it would make sense to a CEO/CFO without the project brief.

---

## System-Wide Impact

**Cinderhaven Data Platform repo:** U2 and U3 add three new `int_*` models to `models/intermediate/`. These will materialize as views (per the platform's dbt_project.yml intermediate layer config). Downstream: the scoring engine in this repo is the only consumer for now, but `int_loaded_contribution_by_sku` is a candidate for reuse in "Where the Money Actually Comes From."

**Velocity Decision Tool:** No changes, but Module 6 should eventually cross-link to this framework. That cross-link is a deferred follow-up task.

**Portfolio site:** Demo URL must be added to the portfolio after deployment. Deferred follow-up task.

---

## Known Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Cinderhaven mart tables don't exist in live DB | Medium | Always query `information_schema.tables` before writing models (U2/U3 approach) |
| COGS formula error (cases vs units) | High (has occurred twice) | Explicitly follow the formula from this plan; add a test with a known B2B order |
| Plotly autorange clips quadrant boundary lines | High (documented failure) | Never use autorange with reference lines; collect all values and set range explicitly |
| Cannibalization DiD not feasible (missing temporal data) | Medium | Spike in U1 determines method before committing to model design |
| Key casing mismatch in JSON silently breaks charts | Medium (has occurred) | Visually verify rendered charts after any pipeline change, not just automated tests |
| `lailara-palette` package path is `published/` not `active/` | Low | Verify path before first import |
| Fly.io Windows export via psycopg2 fails | Medium | Use `flyctl postgres connect` with piped SQL, not psycopg2 local proxy |

---

## Dependencies and Prerequisites

- Cinderhaven Data Platform Postgres must be accessible locally
- `dbt` installed and profile pointed at Cinderhaven Postgres
- Fly.io CLI (`flyctl`) authenticated for DB access
- `lailara-palette` package installed from correct local path (verify: `published/` or `active/`)
- Velocity Decision Tool `calcs.py` and `constants.py` available as reference (read-only)

---

## Deferred Implementation Notes

- Exact quadrant composite score thresholds (set by inspecting calibration output in U4, not predetermined)
- Whether cannibalization uses rigorous or proxy method (determined by U1 spike)
- Whether `int_loaded_contribution_by_sku` is published to the platform's public mart layer (separate platform decision)
- Exact weight slider UI design (implement during U6 to match visual quality bar)
