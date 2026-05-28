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

_DIMENSIONS: tuple[str, ...] = (
    "velocity",
    "contribution_margin",
    "shelf_space_cost",
    "production_complexity",
    "cannibalization_risk",
)


def assign_quadrant(scores: dict[str, int | None]) -> str:
    """Return quadrant label from a dict of dimension scores (1–5 or None).

    scores keys must match DEFAULT_WEIGHTS keys exactly.
    Any None score means insufficient data for that dimension; the SKU
    cannot be placed in a scored quadrant.
    """
    values = [scores[d] for d in _DIMENSIONS]
    if any(v is None for v in values):
        return "insufficient_data"
    red_flags = sum(1 for v in values if v <= 2)
    if red_flags >= 2:
        return "kill"
    if red_flags == 1:
        return "fix_or_kill"
    if min(values) >= 4:
        return "double_down"
    return "maintain"


def compute_weighted_score(
    scores: dict[str, int | None],
    weights: dict[str, float] | None = None,
) -> float | None:
    """Return weighted composite score in [1, 5], or None if any dimension is missing.

    A partial score would be incomparable to fully-scored SKUs, so None is
    returned rather than a misleading number.
    """
    w = weights if weights is not None else DEFAULT_WEIGHTS
    total = sum(w.values())
    if abs(total - 1.0) > 0.01:
        raise ValueError(f"weights must sum to 1.0 (got {total:.4f})")
    if any(scores[d] is None for d in _DIMENSIONS):
        return None
    return round(sum(scores[d] * w[d] for d in _DIMENSIONS), 4)
