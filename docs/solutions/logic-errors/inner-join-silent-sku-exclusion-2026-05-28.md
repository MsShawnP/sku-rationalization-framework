---
title: "INNER JOINs silently drop NULL-dimension SKUs from scoring pipeline"
date: 2026-05-28
category: logic-errors
module: scoring-pipeline
problem_type: logic_error
component: database
severity: critical
symptoms:
  - "Output row count equalled product_master count but any SKU with NULL dimension data would be silently absent — no warning produced"
  - "No error raised — pipeline completed successfully with missing data"
  - "SKUs with NULL dimension values (velocity, margin, shelf cost, complexity) were dropped without warning"
  - "kill/fix/maintain/double-down quadrant assignments reflected incomplete portfolio"
root_cause: logic_error
resolution_type: code_fix
related_components:
  - service_object
  - testing_framework
tags:
  - sql
  - data-integrity
  - null-handling
  - scoring-pipeline
  - left-join
  - silent-failure
  - python
---

# INNER JOINs silently drop NULL-dimension SKUs from scoring pipeline

## Problem

`run_scoring.py` used INNER JOINs against PostgreSQL intermediate views. Any SKU with NULL values in one or more scored dimensions would be silently dropped — no error, no warning, just fewer rows in the output. In the Cinderhaven portfolio (50 SKUs, all with complete dimension data), the output count appeared correct, making the latent bug invisible without an explicit row-count comparison against `product_master`.

## Symptoms

- No exception, no warning, no log message — query completes successfully with fewer rows than `product_master`
- SKUs with NULL `loaded_margin_pct`, `annual_shelf_space_cost`, or `landed_cost_per_unit` would be absent from results entirely
- Missing SKUs are invisible unless the caller explicitly compares output count to `SELECT COUNT(*) FROM raw.product_master`
- Quadrant distributions would be computed over an incomplete portfolio with no indication that rows were excluded

## What Didn't Work

- **Defaulting None dimensions to median score** — rejected; produces confident-looking classifications for SKUs with no supporting data, masking real gaps
- **Filtering incomplete SKUs before scoring** — rejected; the requirement was that incomplete data appears in output as `insufficient_data`, not as absence ("the truth is in the data even if it is different than the story the brief wanted to tell")
- **Assigning a neutral score of 3 to missing dimensions** — rejected as misleading; score 3 implies mediocre data, not absent data
- **The initial INNER JOIN approach (session history)** — the scoring pipeline passed all unit tests and the script exited cleanly. No test exercised a fixture SKU with a NULL dimension value, so the exclusion was invisible. The only logged failure during initial development was an unrelated alias bug (`product_line` referenced from wrong JOIN alias). The silent exclusion was not detected until a code review in a subsequent session.

## Solution

Changed all INNER JOINs to LEFT JOINs, anchored on `raw.product_master` as the authoritative spine. Added NULL propagation through the entire scoring stack so every SKU reaches the output, classified as `insufficient_data` when any core dimension is missing.

**Before — INNER JOINs silently drop NULLs:**

```sql
FROM raw.product_master pm
JOIN (...) v ON pm.sku = v.sku   -- drops SKU if view has no row
JOIN (...) m ON pm.sku = m.sku
JOIN (...) s ON pm.sku = s.sku
JOIN raw.sku_costs sc ON pm.sku = sc.sku
LEFT JOIN (...) c ON pm.sku = c.sku  -- only cannibalization was LEFT
```

**After — LEFT JOINs preserve all SKUs:**

```sql
FROM raw.product_master pm
LEFT JOIN (...) v ON pm.sku = v.sku
LEFT JOIN (...) m ON pm.sku = m.sku
LEFT JOIN (...) s ON pm.sku = s.sku
LEFT JOIN raw.sku_costs sc ON pm.sku = sc.sku
LEFT JOIN (...) c ON pm.sku = c.sku
```

**Python scoring stack changes:**

`src/scoring/dimensions.py` — all four non-cannibalization functions accept and return `None` when their input is `None`. `score_cannibalization_risk` does **not** accept `None` — its signature is `(float) -> int`. The caller in `engine.py` substitutes `0.0` before calling it (see below):

```python
def score_velocity(uspw: float | None) -> int | None:
    if uspw is None:
        return None
    ...

def score_cannibalization_risk(cannibalization_risk: float) -> int:
    # Does NOT accept None — caller must coerce first
    ...
```

`src/scoring/engine.py` — cannibalization coercion happens here, *before* `scores` is assembled. By the time `assign_quadrant` receives the `scores` dict, `scores["cannibalization_risk"]` is always an `int`:

```python
safe_cannibal = cannibalization_risk if cannibalization_risk is not None else 0.0

scores = {
    "velocity": score_velocity(uspw),                          # may be None
    "contribution_margin": score_contribution_margin(loaded_margin_pct),
    "shelf_space_cost": score_shelf_space_cost(annual_shelf_space_cost),
    "production_complexity": score_production_complexity(complexity_ratio),
    "cannibalization_risk": score_cannibalization_risk(safe_cannibal),  # always int
}
```

`src/scoring/quadrants.py` — `assign_quadrant` sees four dimensions that may be `None` and one that is always `int`. The None check fires on any of the four nullable dimensions:

```python
def assign_quadrant(scores: dict[str, int | None]) -> str:
    if any(v is None for v in scores.values()):
        return "insufficient_data"
    ...
```

`run_scoring.py` — four dimensions use `None` passthrough; cannibalization uses the `0.0` coercion path instead. Do not apply the same `if x is not None else None` pattern to `cannibalization_risk` — doing so would pass `None` to `score_cannibalization_risk`, which raises `TypeError`:

```python
uspw=float(row["uspw"]) if row["uspw"] is not None else None,          # None passthrough
loaded_margin_pct=float(row["loaded_margin_pct"]) if row["loaded_margin_pct"] is not None else None,
# ... (same pattern for annual_shelf_space_cost, complexity_ratio)
cannibalization_risk=(
    float(row["cannibalization_risk"])
    if row["cannibalization_risk"] is not None
    else None           # engine.py converts this None → 0.0, not dimensions.py
),
```

New tests in `tests/test_scoring/test_engine.py` cover None propagation per dimension — each asserts that a SKU with one NULL dimension appears in output with quadrant `"insufficient_data"`, not absent.

## Why This Works

An INNER JOIN only produces output rows where the join condition matches on both sides. When a PostgreSQL intermediate view has no row for a SKU — because upstream data was absent, a dbt model's WHERE clause excluded it, or the view was not yet populated — the INNER JOIN discards the `product_master` row entirely. No error is raised because the query is syntactically valid SQL.

LEFT JOIN preserves every row from the left-side table (`product_master`) and fills unmatched columns with NULL. Propagating NULL through the scoring functions and surfacing `insufficient_data` as an explicit quadrant makes the data gap observable in the output rather than hiding it.

Cannibalization is intentionally different: `cannibalization_risk=None` means fewer than 3 solo stores were observed — a data sparsity threshold, not a missing data source. Treating it as `0.0` (score 5, no risk) is correct. Treating it the same as a missing velocity or margin value would incorrectly classify well-distributed SKUs as data-incomplete. (session history)

**Why tests did not catch it:** Unit tests used fixture data where all required fields were populated. Tests passed clean. The exclusion is only observable by comparing output row count against `SELECT COUNT(*) FROM raw.product_master` — a cross-count check that was not part of the test suite or run summary at the time.

## Prevention

- **Assert output row count equals input count.** After every scoring run, compare `len(scored)` to `SELECT COUNT(*) FROM raw.product_master` and log a warning if they differ. `run_scoring.py` now reports `{N} SKUs retrieved ({M} with at least one missing dimension)`. Note: this is currently a print statement, not an exception — a pipeline running non-interactively should promote it to a raised error or non-zero exit.
- **Default to LEFT JOIN when querying from a master spine.** Any query anchored to a single authoritative table (`product_master`, `product`, `customer`) should use LEFT JOIN for all lookups. INNER JOIN is the explicit override that requires a documented reason.
- **Include a NULL-dimension fixture in the test suite per dimension.** At minimum, one test per scored dimension should assert that `None` → `insufficient_data` quadrant (not absent from output). These tests now live in `tests/test_scoring/test_engine.py`.
- **Document the join decision when adding a new data source.** For each dimension joined into a scoring pipeline, decide: does the absence of this data disqualify a record (INNER JOIN) or flag it as incomplete (LEFT JOIN + None)? Record the decision in `DECISIONS.md`.

## Related Issues

- `DECISIONS.md` — compact entry capturing the decision rationale; this doc adds the technical mechanism and prevention checklist
- `docs/scoring_methodology.md` — documents the cannibalization `None`-as-no-signal rule; worth adding a note that all five dimensions are sourced via LEFT JOIN from `raw.product_master` as spine, and that SKUs with missing core dimensions appear as `insufficient_data` rather than being omitted
