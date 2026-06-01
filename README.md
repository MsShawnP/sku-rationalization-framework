# SKU Rationalization Framework

A multi-dimensional SKU scoring and visualization framework for specialty food brands at $10M–$30M revenue. Scores every SKU across five dimensions — velocity, contribution margin, shelf-space cost, production complexity, and cannibalization risk — and classifies each SKU into one of four action buckets: double down, maintain, fix or kill, or kill.

**Demo:** `https://MsShawnP.github.io/sku-rationalization-framework/app/`

---

## What it does

Given a brand's Postgres data, the framework:

1. Scores all 50 SKUs across 5 dimensions using percentile-calibrated thresholds
2. Assigns each SKU to an action bucket based on red-flag counts (not a weighted average)
3. Exports a static JSON snapshot for offline analysis
4. Serves an interactive demo with adjustable dimension weights, ranked charts, and click-through SKU detail

The Cinderhaven case study (included) applies the framework to a 50-SKU portfolio across 6 retailers over a 3-year window. Result: 19 kill candidates, 22 fix-or-kill, 7 maintain, 2 double down.

---

## Stack

- **Scoring engine:** Python 3.13, `psycopg2`
- **Data models:** dbt (Cinderhaven Postgres via Fly.io)
- **Demo tool:** Static HTML + Plotly.js 2.27 + Lailara Design System v2
- **Tests:** pytest (80 unit tests)

---

## Prerequisites

- Python 3.13+
- `pip install -r requirements.txt`
- flyctl proxy running: `flyctl proxy 5432:5432 -a cinderhaven-db`
- `POSTGRES_PASSWORD` env var set (or `.env` in the cinderhaven-data-platform repo)

---

## How to run

### Run tests
```bash
python -m pytest tests/ -v
```

### Recalibrate thresholds from Cinderhaven data
```bash
flyctl proxy 5432:5432 -a cinderhaven-db   # in a separate terminal
python scripts/calibrate.py
```

### Re-score all SKUs and export JSON
```bash
python run_scoring.py
```
Output: `data/cinderhaven_scored.json`

### Run the demo locally
```bash
python -m http.server 8080
# Open: http://localhost:8080/app/
```

---

## Project structure

```
app/                    — static demo tool (HTML + CSS + JS)
  index.html            — portfolio audit page
  css/lailara.css       — Lailara Design System v2 styles
  js/app.js             — charts, sliders, filters, detail card
data/
  cinderhaven_scored.json  — static scored snapshot (all 50 SKUs)
docs/
  scoring_methodology.md   — full methodology, thresholds, caveats
sql/
  diagnostic_queries.sql   — 6 analytical SQL queries for client work
scripts/
  calibrate.py          — writes percentile thresholds to constants.py
src/scoring/
  constants.py          — auto-generated percentile thresholds
  dimensions.py         — five pure scoring functions (score 1–5)
  quadrants.py          — quadrant assignment + weighted composite
  engine.py             — assembles all dimensions for one SKU
tests/test_scoring/
  test_dimensions.py    — 38 tests covering all five scoring functions
  test_quadrants.py     — 16 tests covering quadrant assignment + composite
run_scoring.py          — CLI: query Postgres → score → export JSON
```

---

## Methodology

Thresholds are calibrated from the actual p10/p25/p50/p75/p90 distribution of each dimension across the portfolio. Quadrant assignment uses red-flag counts, not the weighted composite. The composite score ranks SKUs within quadrants; weights (adjustable in the demo) do not affect bucket assignment.

See [docs/scoring_methodology.md](docs/scoring_methodology.md) for full detail, including the cannibalization proxy method and known limitations.

---

## Consulting offer

This framework is the basis of Lailara LLC's **SKU Portfolio Audit** engagement. The engagement delivers:

- Full scored output for your portfolio
- Kill list with quantified annual savings (shelf cost + loaded contribution impact)
- Fix-or-kill action plan with one specific lever per SKU
- Methodology doc and SQL queries for your internal team

Contact: msshawnp@gmail.com
