"""Tests for score_sku() — the assembled SKU record."""

from src.scoring.engine import score_sku
from src.scoring.quadrants import DEFAULT_WEIGHTS
from src.scoring.constants import (
    VELOCITY_P50,
    MARGIN_P50,
    SHELF_P50,
    COMPLEX_P50,
)

# Fixture values that all score 4 (P50 level) → double_down when cannibal = 0
_SKU = "TEST-001"
_LINE = "Snacks"
_FULL = dict(
    sku=_SKU,
    product_line=_LINE,
    uspw=VELOCITY_P50,
    loaded_margin_pct=MARGIN_P50,
    annual_shelf_space_cost=SHELF_P50,
    complexity_ratio=COMPLEX_P50,
    cannibalization_risk=0.0,
)


class TestScoreSkuOutputShape:
    def test_returns_required_keys(self):
        result = score_sku(**_FULL)
        assert set(result) == {
            "sku", "product_line", "raw", "scores", "weighted_score", "quadrant", "weights_used"
        }

    def test_scores_has_five_dimensions(self):
        result = score_sku(**_FULL)
        assert set(result["scores"]) == {
            "velocity", "contribution_margin", "shelf_space_cost",
            "production_complexity", "cannibalization_risk",
        }

    def test_raw_has_five_values(self):
        result = score_sku(**_FULL)
        assert set(result["raw"]) == {
            "uspw", "loaded_margin_pct", "annual_shelf_space_cost",
            "complexity_ratio", "cannibalization_risk",
        }

    def test_sku_and_product_line_passed_through(self):
        result = score_sku(**_FULL)
        assert result["sku"] == _SKU
        assert result["product_line"] == _LINE

    def test_default_weights_used_when_none_passed(self):
        result = score_sku(**_FULL)
        assert result["weights_used"] == DEFAULT_WEIGHTS

    def test_custom_weights_stored(self):
        w = {"velocity": 0.5, "contribution_margin": 0.5,
             "shelf_space_cost": 0.0, "production_complexity": 0.0, "cannibalization_risk": 0.0}
        result = score_sku(**_FULL, weights=w)
        assert result["weights_used"] == w


class TestScoreSkuJsonOutputContract:
    """Verify the value types that app.js depends on.

    If score_sku() changes the types or valid values here, the demo tool
    breaks silently at runtime. These tests catch that at the Python layer.
    """

    _VALID_QUADRANTS = {"double_down", "maintain", "fix_or_kill", "kill", "insufficient_data"}
    _DIMENSIONS = {"velocity", "contribution_margin", "shelf_space_cost",
                   "production_complexity", "cannibalization_risk"}

    def test_score_values_are_integers_1_to_5_for_full_data(self):
        result = score_sku(**_FULL)
        for dim, val in result["scores"].items():
            assert isinstance(val, int), f"{dim} score should be int, got {type(val)}"
            assert 1 <= val <= 5, f"{dim} score {val} is outside [1, 5]"

    def test_weighted_score_is_float_in_range(self):
        result = score_sku(**_FULL)
        assert isinstance(result["weighted_score"], float)
        assert 1.0 <= result["weighted_score"] <= 5.0

    def test_quadrant_is_valid_enum_value(self):
        result = score_sku(**_FULL)
        assert result["quadrant"] in self._VALID_QUADRANTS

    def test_sku_and_product_line_are_strings(self):
        result = score_sku(**_FULL)
        assert isinstance(result["sku"], str)
        assert isinstance(result["product_line"], str)

    def test_output_is_json_serializable(self):
        import json
        result = score_sku(**_FULL)
        serialized = json.dumps(result)  # raises if not serializable
        roundtripped = json.loads(serialized)
        assert roundtripped["sku"] == _SKU
        assert roundtripped["quadrant"] == result["quadrant"]

    def test_insufficient_data_sku_has_none_weighted_score(self):
        result = score_sku(
            sku="MISSING-001", product_line="Test",
            uspw=None,
            loaded_margin_pct=None,
            annual_shelf_space_cost=None,
            complexity_ratio=None,
            cannibalization_risk=None,
        )
        assert result["quadrant"] == "insufficient_data"
        assert result["weighted_score"] is None


class TestScoreSkuCannibalizationNone:
    """cannibalization_risk=None means no signal — should not count as missing data."""

    def test_none_cannibalization_treated_as_zero(self):
        result = score_sku(**{**_FULL, "cannibalization_risk": None})
        assert result["raw"]["cannibalization_risk"] == 0.0

    def test_none_cannibalization_scores_5(self):
        result = score_sku(**{**_FULL, "cannibalization_risk": None})
        assert result["scores"]["cannibalization_risk"] == 5

    def test_none_cannibalization_does_not_produce_insufficient_data(self):
        result = score_sku(**{**_FULL, "cannibalization_risk": None})
        assert result["quadrant"] != "insufficient_data"


class TestScoreSkuMissingDimensions:
    """Any None dimension other than cannibalization = insufficient data."""

    def test_none_uspw_gives_insufficient_data_quadrant(self):
        result = score_sku(**{**_FULL, "uspw": None})
        assert result["quadrant"] == "insufficient_data"

    def test_none_uspw_gives_none_weighted_score(self):
        result = score_sku(**{**_FULL, "uspw": None})
        assert result["weighted_score"] is None

    def test_none_uspw_stored_in_raw(self):
        result = score_sku(**{**_FULL, "uspw": None})
        assert result["raw"]["uspw"] is None

    def test_none_uspw_gives_none_velocity_score(self):
        result = score_sku(**{**_FULL, "uspw": None})
        assert result["scores"]["velocity"] is None

    def test_none_margin_gives_insufficient_data_quadrant(self):
        result = score_sku(**{**_FULL, "loaded_margin_pct": None})
        assert result["quadrant"] == "insufficient_data"

    def test_none_shelf_gives_insufficient_data_quadrant(self):
        result = score_sku(**{**_FULL, "annual_shelf_space_cost": None})
        assert result["quadrant"] == "insufficient_data"

    def test_none_complexity_gives_insufficient_data_quadrant(self):
        result = score_sku(**{**_FULL, "complexity_ratio": None})
        assert result["quadrant"] == "insufficient_data"

    def test_multiple_none_dimensions_still_insufficient_data(self):
        result = score_sku(**{**_FULL, "uspw": None, "loaded_margin_pct": None})
        assert result["quadrant"] == "insufficient_data"
        assert result["weighted_score"] is None


class TestScoreSkuFullDataScoring:
    """End-to-end: known inputs produce expected scores and quadrant."""

    def test_p50_inputs_score_4_on_all_dimensions(self):
        result = score_sku(**_FULL)
        # P50 → score 4 for all four continuous dimensions
        assert result["scores"]["velocity"] == 4
        assert result["scores"]["contribution_margin"] == 4
        assert result["scores"]["shelf_space_cost"] == 4
        assert result["scores"]["production_complexity"] == 4
        assert result["scores"]["cannibalization_risk"] == 5  # 0.0 → 5

    def test_p50_inputs_produce_double_down_quadrant(self):
        # min score = 4, all >= 4 → double_down
        result = score_sku(**_FULL)
        assert result["quadrant"] == "double_down"

    def test_weighted_score_is_float_between_1_and_5(self):
        result = score_sku(**_FULL)
        assert isinstance(result["weighted_score"], float)
        assert 1.0 <= result["weighted_score"] <= 5.0
