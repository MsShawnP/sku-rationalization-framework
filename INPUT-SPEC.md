# INPUT-SPEC — sku-rationalization-framework (client mode)

What to hand the tool in a client engagement. One SKU file (one row per SKU),
CSV or XLSX. Derived from the scoring engine (`src/scoring/engine.py::score_sku`,
`dimensions.py`), not the README.

## Required columns

| Canonical | Type | Used for |
|---|---|---|
| `sku` | identifier (text, unique) | SKU code. §1 |
| `product_line` | string | Product line. §1 |

## Scoring dimensions (optional — blanks leave a dimension unscored)

The five dimensions the engine scores 0–5 and weights into a quadrant. Any blank
leaves that dimension unscored (`None`); a SKU missing too many dimensions is
classified **`insufficient_data`**, never scored with invented numbers.

| Canonical | Type | Meaning |
|---|---|---|
| `uspw` | number | Units per store per week (velocity). |
| `loaded_margin_pct` | number | Loaded contribution-margin rate (may be negative). |
| `annual_shelf_space_cost` | number ≥ 0 | Annual shelf-space cost. |
| `complexity_ratio` | number ≥ 0 | Production complexity ratio. |
| `cannibalization_risk` | number (0..1) | Cannibalization risk; blank → 0 (absence of signal ≠ missing data). |

## Weights (engagement.yml, optional)

```yaml
as_of_date: "2026-01-31"          # analysis anchor; NEVER today's date
basis:
  window_label: "2023–2026"
  weights:                         # optional; defaults to 0.2 each
    velocity: 0.2
    contribution_margin: 0.2
    shelf_space_cost: 0.2
    production_complexity: 0.2
    cannibalization_risk: 0.2
```

## Run

```bash
pip install -e ../engagement-template/lib
python client_mode.py --config engagement.yml --input client-data/skus.csv \
    --out client-output [--final]
```

Output to `client-output/` (gitignored): a branded, provenance-footed,
DRAFT-watermarked `sku-rationalization-summary.html` (quadrant distribution +
per-SKU quadrant and weighted score) + `json/summary.json`; or a Data Readiness
Report if a required column is missing. Client SKUs are scored with the **same
engine** the demo uses (`score_sku`); the demo dataset is never edited (golden-locked).
