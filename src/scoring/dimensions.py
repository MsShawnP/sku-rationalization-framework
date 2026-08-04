"""Pure scoring functions for all five SKU rationalization dimensions.

Each function takes a raw measured value and returns a score 1–5.
5 = best performance, 1 = worst performance.

Thresholds are calibrated from actual Cinderhaven data percentile
distributions. For "lower is better" dimensions the scoring is inverted:
a low raw value earns a high score.

No database access, no side effects. Tests live in tests/test_scoring/.
"""

from __future__ import annotations

from src.scoring.constants import (
    CANNIBAL_HIGH,
    CANNIBAL_P50,
    CANNIBAL_VERY_HIGH,
    COMPLEX_P25,
    COMPLEX_P50,
    COMPLEX_P75,
    COMPLEX_P90,
    MARGIN_P10,
    MARGIN_P25,
    MARGIN_P50,
    MARGIN_P75,
    SHELF_P25,
    SHELF_P50,
    SHELF_P75,
    SHELF_P90,
    VELOCITY_P10,
    VELOCITY_P25,
    VELOCITY_P50,
    VELOCITY_P75,
)


def score_velocity(uspw: float | None) -> int | None:
    """Score velocity (units/store/week). Higher is better."""
    if uspw is None:
        return None
    if uspw >= VELOCITY_P75:
        return 5
    if uspw >= VELOCITY_P50:
        return 4
    if uspw >= VELOCITY_P25:
        return 3
    if uspw >= VELOCITY_P10:
        return 2
    return 1


def score_contribution_margin(loaded_margin_pct: float | None) -> int | None:
    """Score loaded contribution margin rate. Higher (less negative) is better.

    All Cinderhaven SKUs have negative loaded margins after full cost loading;
    scoring is portfolio-relative — score 5 = least negative in the portfolio.
    """
    if loaded_margin_pct is None:
        return None
    if loaded_margin_pct >= MARGIN_P75:
        return 5
    if loaded_margin_pct >= MARGIN_P50:
        return 4
    if loaded_margin_pct >= MARGIN_P25:
        return 3
    if loaded_margin_pct >= MARGIN_P10:
        return 2
    return 1


def score_shelf_space_cost(annual_cost: float | None) -> int | None:
    """Score annual shelf-space cost. Lower is better (inverted scoring)."""
    if annual_cost is None:
        return None
    if annual_cost <= SHELF_P25:
        return 5
    if annual_cost <= SHELF_P50:
        return 4
    if annual_cost <= SHELF_P75:
        return 3
    if annual_cost <= SHELF_P90:
        return 2
    return 1


def score_production_complexity(complexity_ratio: float | None) -> int | None:
    """Score production complexity (landed_cost/msrp proxy). Lower ratio is better.

    A lower landed_cost/msrp ratio means the product is simpler to produce
    relative to its price, indicating lower ingredient and manufacturing complexity.
    """
    if complexity_ratio is None:
        return None
    if complexity_ratio <= COMPLEX_P25:
        return 5
    if complexity_ratio <= COMPLEX_P50:
        return 4
    if complexity_ratio <= COMPLEX_P75:
        return 3
    if complexity_ratio <= COMPLEX_P90:
        return 2
    return 1


def score_cannibalization_risk(cannibalization_risk: float) -> int:
    """Score cannibalization risk. Lower risk (closer to 0) is better.

    cannibalization_risk is the inverted velocity delta:
      max(0, -(shared_uspw - solo_uspw) / solo_uspw)
    A value of 0 means no measurable cannibalization signal.
    A positive value means velocity drops when sibling SKUs are present.

    Caller passes 0.0 when the raw value is None (< 3 solo stores);
    absence of signal is treated as no penalty, not missing data.
    """
    if cannibalization_risk == 0.0:
        return 5
    if cannibalization_risk <= CANNIBAL_P50:
        return 4
    if cannibalization_risk <= CANNIBAL_HIGH:
        return 3
    if cannibalization_risk <= CANNIBAL_VERY_HIGH:
        return 2
    return 1
