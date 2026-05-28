"""Assemble all five dimension scores for a single SKU row."""

from __future__ import annotations

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
    uspw: float,
    loaded_margin_pct: float,
    annual_shelf_space_cost: float,
    complexity_ratio: float,
    cannibalization_risk: float,
    weights: dict[str, float] | None = None,
) -> dict:
    """Return a fully scored SKU record.

    cannibalization_risk of None (SKU had fewer than 3 solo stores) is
    treated as 0.0 — no measurable signal, so no penalty.
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
            "uspw": round(uspw, 4),
            "loaded_margin_pct": round(loaded_margin_pct, 4),
            "annual_shelf_space_cost": round(annual_shelf_space_cost, 2),
            "complexity_ratio": round(complexity_ratio, 4),
            "cannibalization_risk": round(safe_cannibal, 4),
        },
        "scores": scores,
        "weighted_score": compute_weighted_score(scores, weights),
        "quadrant": assign_quadrant(scores),
        "weights_used": weights if weights is not None else DEFAULT_WEIGHTS,
    }
