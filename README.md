# SKU Rationalization Framework — score every SKU, know exactly which ones to cut

A multi-dimensional SKU scoring and visualization framework for specialty food brands in the $10M–$30M revenue range. It turns raw sales, cost, and shelf data into a ranked kill/keep decision for every product in the portfolio.

**Live demo:** https://sku.lailarallc.com

## What it does

Given a brand's Postgres data, the framework:

1. Scores every SKU (1–5) across five dimensions: velocity, contribution margin, shelf-space cost, production complexity, and cannibalization risk
2. Calibrates scoring thresholds from the portfolio's own p10/p25/p50/p75/p90 distributions — no arbitrary cutoffs (cannibalization is the one exception: its high/very-high cutoffs come from the pre-zeroing pairs distribution, where the metric is defined — see [docs/scoring_methodology.md](docs/scoring_methodology.md))
3. Assigns each SKU to one of four action buckets — double down, maintain, fix or kill, or kill — based on red-flag counts, not a weighted average that can hide a fatal flaw
4. Exports a static JSON snapshot and serves an interactive demo with adjustable dimension weights, ranked charts, and click-through SKU detail

The included Cinderhaven case study applies the framework to a 50-SKU portfolio across 6 retailers over a 3-year window. Result: 19 kill, 14 fix-or-kill, 16 maintain, 1 double down.

## Why it matters

Mid-size food brands routinely carry SKUs that lose money on every unit once trade spend, slotting, and shelf costs are fully loaded — but gut-feel portfolio reviews protect them. This framework replaces that debate with evidence:

- A defensible, data-calibrated kill list instead of opinions about "brand-building" SKUs
- Shelf-space cost made explicit, so slow movers can't hide behind gross margin
- Cannibalization measured (via a cross-sectional velocity proxy), so cutting a SKU doesn't silently transfer its problem to a sibling product
- Adjustable weights in the demo let stakeholders stress-test the ranking live — bucket assignment stays fixed, so the conversation can't be gamed

In the case study, 33 of 50 SKUs (66%) landed in kill or fix-or-kill — a typical outcome for portfolios that have grown by line extension.

## Quick start

Requires Python 3.13+.

```bash
pip install -r requirements.txt

# Run the test suite (92 tests, no database needed)
python -m pytest tests/ -v

# View the demo locally (uses the committed data snapshot)
python -m http.server 8080
# Open: http://localhost:8080/app/
```

Re-scoring against the live Cinderhaven database additionally requires a flyctl proxy and credentials (`POSTGRES_PASSWORD` env var, or point `CINDERHAVEN_ENV` at a `.env` file):

```bash
flyctl proxy 5432:5432 -a cinderhaven-db   # in a separate terminal

# Recalibrate percentile thresholds into src/scoring/constants.py
python scripts/calibrate.py

# Score all SKUs and write data/cinderhaven_scored.json
python run_scoring.py
python run_scoring.py --weights vel=0.4,margin=0.3,shelf=0.1,complexity=0.1,cannibal=0.1
```

## Tech stack

- **Scoring engine:** Python 3.13, `psycopg2`
- **Data source:** Cinderhaven Postgres on Fly.io (dbt-modeled intermediate views)
- **Demo tool:** Static HTML + Plotly.js 2.27 + Lailara Design System v2 (no build step)
- **Tests:** pytest — 92 tests, including a canonical-regression suite guarding the scored JSON artifact
- **Deployment:** nginx (Docker) on Fly.io (`Dockerfile`, `fly.toml`)

## Project structure

```
run_scoring.py            — CLI: query Postgres → score → export JSON
scripts/calibrate.py      — writes percentile thresholds to src/scoring/constants.py
src/scoring/
  dimensions.py           — five pure scoring functions (score 1–5)
  quadrants.py            — bucket assignment (red-flag counts) + weighted composite
  engine.py               — assembles all dimensions for one SKU
  constants.py            — auto-generated percentile thresholds
app/                      — static demo (index.html, js/app.js, css/lailara.css)
data/cinderhaven_scored.json — scored snapshot of all 50 SKUs
sql/diagnostic_queries.sql   — 6 analytical SQL queries for client work
docs/scoring_methodology.md  — full methodology, thresholds, caveats
tests/                    — dimension, engine, quadrant, and regression tests
```

See [docs/scoring_methodology.md](docs/scoring_methodology.md) for full methodology detail, including the cannibalization proxy method and known limitations.

## Data contract

The case study consumes the full Cinderhaven canonical dataset:

- **50 SKUs** across 5 product lines (Artisan Sauces, Pantry Staples, Specialty Condiments, Dried Goods, Snack Bites)
- **6 contracted retailers:** Walmart, Costco, Whole Foods, Sprouts, Kroger, Regional Group
- **3 distributors:** UNFI, KeHE, DPI Northwest
- **1 DTC channel:** Shopify

## Consulting offer

This framework is the basis of Lailara LLC's SKU Portfolio Audit engagement, which delivers:

- Full scored output for your portfolio
- Kill list with quantified annual savings (shelf cost + loaded contribution impact)
- Fix-or-kill action plan with one specific lever per SKU
- Methodology doc and SQL queries for your internal team

Contact: msshawnp@gmail.com

## Client engagement use

The demo renders the committed Cinderhaven scored dataset. To score a **client's
own SKU portfolio** in place — validated, never committed, never deployed — use
client mode (see [INPUT-SPEC.md](INPUT-SPEC.md)):

```bash
pip install -e ../engagement-template/lib      # the shared lailara_engagement scaffold
python client_mode.py --config engagement.yml --input client-data/skus.csv \
    --out client-output [--final]
```

It scores each SKU with the **same engine** the demo uses (`score_sku`) across the
five weighted dimensions and assigns a quadrant; SKUs missing too many dimensions
are classed "Insufficient data", never guessed. Output to `client-output/`
(gitignored): a branded, provenance-footed, DRAFT-watermarked
`sku-rationalization-summary.html` + `summary.json`, or a Data Readiness Report if
a required column is missing. The demo dataset is never edited (golden-locked).

## License

MIT — see [LICENSE](LICENSE).

---
Built by [Lailara LLC](https://lailarallc.com) — data hygiene and analytics consulting for specialty food brands scaling into national retail.
