# SKU Rationalization Scoring Methodology

**Version:** 1.0  
**Data source:** Cinderhaven Postgres, 2023–2026 window  
**Portfolio:** 50 SKUs, 5 product lines, 6 retailers

---

## Overview

Every SKU in the portfolio is scored across five dimensions. Each dimension produces a score from 1 (worst) to 5 (best), calibrated against the actual distribution of that dimension across the portfolio. The scores are combined into a weighted composite and each SKU is assigned to one of four action buckets.

The framework answers: *which SKUs should be killed, fixed, maintained, or doubled down on — and what does each decision cost or save?*

---

## The Five Dimensions

### 1. Velocity
**What it measures:** Average units sold per store per week (USPW).  
**Direction:** Higher is better.  
**Data source:** `raw.scan_data`, aggregated per SKU across the full data window.

| Score | Threshold |
|-------|-----------|
| 5 | ≥ 9.95 USPW (p75) |
| 4 | ≥ 9.40 USPW (p50) |
| 3 | ≥ 8.37 USPW (p25) |
| 2 | ≥ 7.16 USPW (p10) |
| 1 | < 7.16 USPW |

### 2. Contribution Margin
**What it measures:** Loaded contribution margin as a percentage of gross revenue, after deducting COGS, trade spend, chargebacks, and allocated retailer deductions.  
**Direction:** Higher (less negative) is better. All Cinderhaven SKUs carry negative loaded margins after full cost loading; scoring is portfolio-relative.  
**Data source:** `public_intermediate.int_loaded_contribution_by_sku`

| Score | Threshold |
|-------|-----------|
| 5 | ≥ −4.38% (p75 — least negative) |
| 4 | ≥ −4.77% (p50) |
| 3 | ≥ −6.98% (p25) |
| 2 | ≥ −7.81% (p10) |
| 1 | < −7.81% |

**COGS formula (B2B):** `units_ordered × case_pack_qty × cogs_per_unit`  
(cases shipped × units per case × cost per unit)

### 3. Shelf Space Cost
**What it measures:** Annual cost of maintaining shelf presence, combining actual promotional spend with a $400/store/year overhead proxy for compliance, data, and resets.  
**Direction:** Lower is better (inverted scoring).  
**Data source:** `public_intermediate.int_shelf_space_cost_by_sku`

| Score | Threshold |
|-------|-----------|
| 5 | ≤ $82,449/year (p25 — lowest cost) |
| 4 | ≤ $85,830/year (p50) |
| 3 | ≤ $88,168/year (p75) |
| 2 | ≤ $91,381/year (p90) |
| 1 | > $91,381/year |

### 4. Production Complexity
**What it measures:** Ratio of landed cost per unit to MSRP (`landed_cost/msrp`). A lower ratio signals a simpler product relative to its price point — lower ingredient and manufacturing complexity.  
**Direction:** Lower is better (inverted scoring).  
**Data source:** `raw.sku_costs` joined to `raw.product_master`

| Score | Threshold |
|-------|-----------|
| 5 | ≤ 0.2475 (p25 — lowest ratio) |
| 4 | ≤ 0.2701 (p50) |
| 3 | ≤ 0.3012 (p75) |
| 2 | ≤ 0.3167 (p90) |
| 1 | > 0.3167 |

### 5. Cannibalization Risk
**What it measures:** Velocity penalty when sibling SKUs (same product line) are co-distributed in the same store. Expressed as the inverted velocity delta: `max(0, -(shared_uspw − solo_uspw) / solo_uspw)`. A value of 0 means no measurable cannibalization.  
**Direction:** Lower is better (inverted scoring).  
**Data source:** `public_intermediate.int_cannibalization_pairs`

**Methodology note:** This is a *proxy* (cross-sectional velocity comparison), not a rigorous difference-in-differences estimate. All 50 Cinderhaven SKUs were authorized within the same six-month window (January–June 2024), leaving insufficient pre-variant temporal depth for DiD. The proxy compares velocity in stores where a SKU is alone in its product line versus stores where sibling SKUs are also present. SKUs with fewer than 3 solo stores are treated as having no measurable signal (score 5).

| Score | Threshold |
|-------|-----------|
| 5 | = 0.000 (no signal) |
| 4 | ≤ 0.046 (p50) |
| 3 | ≤ 0.120 (p75) |
| 2 | ≤ 0.250 (p90) |
| 1 | > 0.250 |

---

## Threshold Calibration

All thresholds are derived from the actual percentile distribution of each dimension across the 50-SKU portfolio. They are not intuition-based.

To recalibrate against updated data:
```bash
flyctl proxy 5432:5432 -a cinderhaven-db   # in a separate terminal
python scripts/calibrate.py
```

This overwrites `src/scoring/constants.py` with new percentile values. Recalibrate whenever the underlying data window changes materially.

---

## Quadrant Assignment

Quadrant is determined by counting *red flags* — dimensions that score 2 or below — not by the weighted composite score. The composite score ranks SKUs within quadrants; it does not determine the quadrant.

| Red flag count | Action bucket |
|----------------|---------------|
| 2 or more | **Kill** — multiple structural failures; candidate for discontinuation |
| Exactly 1 | **Fix or Kill** — one critical weakness; address it or cut |
| 0, but min score < 4 | **Maintain** — no critical failures; hold and optimize |
| 0, and all scores ≥ 4 | **Double Down** — strong across all dimensions; invest and protect |

---

## Weighted Composite Score

The composite score (1–5) is computed as:

```
score = Σ(dimension_score × weight)
```

Default weights are equal (20% per dimension). The interactive demo tool at `app/index.html` allows weights to be adjusted per the client's priorities. Adjusting weights re-ranks the composite but does not change action bucket assignments.

---

## Limitations and Caveats

1. **Cannibalization is a proxy.** Cross-sectional comparison is directional, not causal. A positive cannibalization signal may reflect store-mix differences rather than true demand transfer. Rigorous DiD would require a longer pre-authorization window.

2. **All margins are negative.** Cinderhaven's fully loaded margins are negative across the portfolio after accounting for COGS, trade spend, chargebacks, and deductions. The scoring is portfolio-relative: score 5 means "least negative," not profitable.

3. **Thresholds are portfolio-relative.** A SKU that scores 5 on velocity in this portfolio might score 3 in a different brand's portfolio. Thresholds should be recalibrated for each new client engagement.

4. **The $400/store/year overhead proxy** for shelf space is an estimate. It covers data compliance, reset labor, and retailer relationship overhead. Adjust this constant in `int_shelf_space_cost_by_sku.sql` if the client has actuals.

5. **Complexity proxy does not capture R&D or packaging complexity.** It uses `landed_cost/MSRP` as a signal only. A more rigorous version would require a bill-of-materials and production time data.
