"""Assemble all five dimension scores for a single SKU row."""

from __future__ import annotations

from typing import Any

from src.scoring.dimensions import (
    score_cannibalization_risk,
    score_contribution_margin,
    score_production_complexity,
    score_shelf_space_cost,
    score_velocity,
)
from src.scoring.quadrants import assign_quadrant, compute_weighted_score, DEFAULT_WEIGHTS


def score_sku(
    sku: str,
    product_line: str,
    uspw: float | None,
    loaded_margin_pct: float | None,
    annual_shelf_space_cost: float | None,
    complexity_ratio: float | None,
    cannibalization_risk: float | None,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return a fully scored SKU record.

    Any dimension except cannibalization_risk may be None when the underlying
    table has no row for this SKU — those SKUs are classified as
    "insufficient_data" rather than scored normally.

    cannibalization_risk of None (fewer than 3 solo stores) is treated as 0.0:
    absence of a cannibalization signal is not the same as missing data.
    """
    safe_cannibal = cannibalization_risk if cannibalization_risk is not None else 0.0

    scores = {
        "velocity": score_velocity(uspw),
        "contribution_margin": score_contribution_margin(loaded_margin_pct),
        "shelf_space_cost": score_shelf_space_cost(annual_shelf_space_cost),
        "production_complexity": score_production_complexity(complexity_ratio),
        "cannibalization_risk": score_cannibalization_risk(safe_cannibal),
    }

    return {
        "sku": sku,
        "product_line": product_line,
        "raw": {
            "uspw": round(uspw, 4) if uspw is not None else None,
            "loaded_margin_pct": round(loaded_margin_pct, 4) if loaded_margin_pct is not None else None,
            "annual_shelf_space_cost": round(annual_shelf_space_cost, 2) if annual_shelf_space_cost is not None else None,
            "complexity_ratio": round(complexity_ratio, 4) if complexity_ratio is not None else None,
            "cannibalization_risk": round(safe_cannibal, 4),
        },
        "scores": scores,
        "weighted_score": compute_weighted_score(scores, weights),
        "quadrant": assign_quadrant(scores),
        "weights_used": (weights if weights is not None else DEFAULT_WEIGHTS).copy(),
    }
