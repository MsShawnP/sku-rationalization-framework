"""Quadrant assignment and weighted composite score for SKU rationalization.

Quadrant rules (applied in order):
  kill        — 2+ dimensions score <= 2
  fix_or_kill — exactly 1 dimension scores <= 2
  double_down — no red flags AND every dimension scores >= 4
  maintain    — no red flags, but at least one dimension scores 3

Weighted composite is computed in [1, 5] space using caller-supplied weights.
Default weights (equal) are 0.20 per dimension.
"""

from __future__ import annotations

DEFAULT_WEIGHTS: dict[str, float] = {
    "velocity": 0.20,
    "contribution_margin": 0.20,
    "shelf_space_cost": 0.20,
    "production_complexity": 0.20,
    "cannibalization_risk": 0.20,
}

_DIMENSIONS = list(DEFAULT_WEIGHTS)


def assign_quadrant(scores: dict[str, int]) -> str:
    """Return quadrant label from a dict of dimension scores (1–5).

    scores keys must match DEFAULT_WEIGHTS keys exactly.
    """
    values = [scores[d] for d in _DIMENSIONS]
    red_flags = sum(1 for v in values if v <= 2)
    if red_flags >= 2:
        return "kill"
    if red_flags == 1:
        return "fix_or_kill"
    if min(values) >= 4:
        return "double_down"
    return "maintain"


def compute_weighted_score(
    scores: dict[str, int],
    weights: dict[str, float] | None = None,
) -> float:
    """Return weighted composite score in [1, 5].

    weights must sum to 1.0; defaults to equal 20% per dimension.
    """
    w = weights if weights is not None else DEFAULT_WEIGHTS
    return round(sum(scores[d] * w[d] for d in _DIMENSIONS), 4)
