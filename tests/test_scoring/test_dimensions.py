"""Tests for the five pure dimension scoring functions."""

import pytest
from src.scoring.dimensions import (
    score_velocity,
    score_contribution_margin,
    score_shelf_space_cost,
    score_production_complexity,
    score_cannibalization_risk,
)
from src.scoring.constants import (
    VELOCITY_P10, VELOCITY_P25, VELOCITY_P50, VELOCITY_P75, VELOCITY_P90,
    MARGIN_P10, MARGIN_P25, MARGIN_P50, MARGIN_P75, MARGIN_P90,
    SHELF_P10, SHELF_P25, SHELF_P50, SHELF_P75, SHELF_P90,
    COMPLEX_P10, COMPLEX_P25, COMPLEX_P50, COMPLEX_P75, COMPLEX_P90,
    CANNIBAL_P50, CANNIBAL_HIGH, CANNIBAL_VERY_HIGH,
)


# --- score_velocity ---

class TestScoreVelocity:
    def test_at_p75_scores_5(self):
        assert score_velocity(VELOCITY_P75) == 5

    def test_above_p75_scores_5(self):
        assert score_velocity(VELOCITY_P75 + 1) == 5

    def test_at_p50_scores_4(self):
        assert score_velocity(VELOCITY_P50) == 4

    def test_between_p50_and_p75_scores_4(self):
        assert score_velocity((VELOCITY_P50 + VELOCITY_P75) / 2) == 4

    def test_at_p25_scores_3(self):
        assert score_velocity(VELOCITY_P25) == 3

    def test_at_p10_scores_2(self):
        assert score_velocity(VELOCITY_P10) == 2

    def test_below_p10_scores_1(self):
        assert score_velocity(VELOCITY_P10 - 0.01) == 1

    def test_zero_scores_1(self):
        assert score_velocity(0.0) == 1

    def test_return_type_is_int(self):
        assert isinstance(score_velocity(10.0), int)


# --- score_contribution_margin ---

class TestScoreContributionMargin:
    def test_at_p75_scores_5(self):
        assert score_contribution_margin(MARGIN_P75) == 5

    def test_above_p75_scores_5(self):
        assert score_contribution_margin(MARGIN_P75 + 0.1) == 5

    def test_at_p50_scores_4(self):
        assert score_contribution_margin(MARGIN_P50) == 4

    def test_at_p25_scores_3(self):
        assert score_contribution_margin(MARGIN_P25) == 3

    def test_at_p10_scores_2(self):
        assert score_contribution_margin(MARGIN_P10) == 2

    def test_below_p10_scores_1(self):
        assert score_contribution_margin(MARGIN_P10 - 0.1) == 1

    def test_all_margins_negative(self):
        # Whole portfolio has negative loaded margins — score 5 is "least negative"
        assert score_contribution_margin(-4.0) == 5
        assert score_contribution_margin(-8.0) == 1


# --- score_shelf_space_cost ---

class TestScoreShelfSpaceCost:
    def test_at_p25_scores_5(self):
        assert score_shelf_space_cost(SHELF_P25) == 5

    def test_below_p25_scores_5(self):
        assert score_shelf_space_cost(SHELF_P25 - 1) == 5

    def test_at_p50_scores_4(self):
        assert score_shelf_space_cost(SHELF_P50) == 4

    def test_at_p75_scores_3(self):
        assert score_shelf_space_cost(SHELF_P75) == 3

    def test_at_p90_scores_2(self):
        assert score_shelf_space_cost(SHELF_P90) == 2

    def test_above_p90_scores_1(self):
        assert score_shelf_space_cost(SHELF_P90 + 1) == 1

    def test_lower_cost_better(self):
        assert score_shelf_space_cost(SHELF_P10) == 5
        assert score_shelf_space_cost(SHELF_P90 + 100) == 1


# --- score_production_complexity ---

class TestScoreProductionComplexity:
    def test_at_p25_scores_5(self):
        assert score_production_complexity(COMPLEX_P25) == 5

    def test_below_p25_scores_5(self):
        assert score_production_complexity(COMPLEX_P25 - 0.001) == 5

    def test_at_p50_scores_4(self):
        assert score_production_complexity(COMPLEX_P50) == 4

    def test_at_p75_scores_3(self):
        assert score_production_complexity(COMPLEX_P75) == 3

    def test_at_p90_scores_2(self):
        assert score_production_complexity(COMPLEX_P90) == 2

    def test_above_p90_scores_1(self):
        assert score_production_complexity(COMPLEX_P90 + 0.01) == 1

    def test_very_low_ratio_scores_5(self):
        assert score_production_complexity(0.10) == 5


# --- score_cannibalization_risk ---

class TestScoreCannibalizationRisk:
    def test_zero_scores_5(self):
        assert score_cannibalization_risk(0.0) == 5

    def test_at_p50_scores_5_when_p50_is_zero(self):
        # After recalibration, CANNIBAL_P50 = 0.0 — exact zero triggers score 5
        assert score_cannibalization_risk(CANNIBAL_P50) == 5

    def test_small_positive_scores_3_when_p50_is_zero(self):
        # With CANNIBAL_P50 = 0.0, any nonzero value below the HIGH cutoff scores 3
        assert score_cannibalization_risk(0.0001) == 3

    def test_at_high_cutoff_scores_3(self):
        assert score_cannibalization_risk(CANNIBAL_HIGH) == 3

    def test_at_very_high_cutoff_scores_2(self):
        assert score_cannibalization_risk(CANNIBAL_VERY_HIGH) == 2

    def test_above_very_high_cutoff_scores_1(self):
        assert score_cannibalization_risk(CANNIBAL_VERY_HIGH + 0.01) == 1

    def test_return_type_is_int(self):
        assert isinstance(score_cannibalization_risk(0.0), int)
