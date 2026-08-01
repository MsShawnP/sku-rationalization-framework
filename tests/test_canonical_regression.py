"""Cinderhaven canonical data regression tests for sku-rationalization-framework.

Verifies the baked scored JSON artifact matches the Cinderhaven data contract.

Canonical contract:
    - 50 SKUs, 5 product lines, 6 retailers
    - Retailers: Walmart, Costco, Whole Foods, Sprouts, Kroger, Regional Group

This repo's scope:
    - 50 SKUs scored into 4 quadrants (kill, fix_or_kill, maintain, double_down).
    - 5 product lines.
    - Retailer dimension not directly in scored output (SKU-level scoring).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "cinderhaven_scored.json"

# Canonical counts from the vendored canon, not hardcoded.
CANON = json.loads((ROOT / "reference" / "canonical_values.json").read_text(encoding="utf-8"))
CANON_SKUS = CANON["universe"]["skus_total"]["all_time"]
CANON_LINES = CANON["universe"]["product_lines"]["all_time"]


@pytest.fixture(scope="module")
def scored():
    assert DATA_PATH.exists(), f"Scored data not found: {DATA_PATH}"
    return json.loads(DATA_PATH.read_text())


class TestCinderhavenCanonicalRegression:
    """Guard-rails for the baked Cinderhaven scored SKU dataset."""

    # ------------------------------------------------------------------
    # SKU count (canonical: 50)
    # ------------------------------------------------------------------

    def test_sku_count_canonical(self, scored):
        """Canonical 50 SKUs."""
        assert len(scored["skus"]) == CANON_SKUS, (
            f"Expected {CANON_SKUS} SKUs (canon), got {len(scored['skus'])}"
        )

    def test_meta_sku_count_matches(self, scored):
        """meta.sku_count should match actual array length."""
        assert scored["meta"]["sku_count"] == len(scored["skus"]), (
            f"meta.sku_count={scored['meta']['sku_count']} but "
            f"array length={len(scored['skus'])}"
        )

    # ------------------------------------------------------------------
    # Product lines (canonical: 5)
    # ------------------------------------------------------------------

    def test_product_line_count(self, scored):
        lines = {s["product_line"] for s in scored["skus"]}
        assert len(lines) == CANON_LINES, f"Expected {CANON_LINES} product lines (canon), got {len(lines)}: {lines}"

    def test_product_line_names(self, scored):
        lines = {s["product_line"] for s in scored["skus"]}
        expected = {
            "Artisan Sauces", "Specialty Condiments", "Pantry Staples",
            "Dried Goods", "Snack Bites",
        }
        assert lines == expected, f"Product line mismatch: {lines}"

    # ------------------------------------------------------------------
    # Quadrant counts
    # ------------------------------------------------------------------

    def test_quadrant_count_kill(self, scored):
        count = sum(1 for s in scored["skus"] if s["quadrant"] == "kill")
        assert count == 19, f"Expected 19 kill, got {count}"

    def test_quadrant_count_fix_or_kill(self, scored):
        count = sum(1 for s in scored["skus"] if s["quadrant"] == "fix_or_kill")
        assert count == 14, f"Expected 14 fix_or_kill, got {count}"

    def test_quadrant_count_maintain(self, scored):
        count = sum(1 for s in scored["skus"] if s["quadrant"] == "maintain")
        assert count == 16, f"Expected 16 maintain, got {count}"

    def test_quadrant_count_double_down(self, scored):
        count = sum(1 for s in scored["skus"] if s["quadrant"] == "double_down")
        assert count == 1, f"Expected 1 double_down, got {count}"

    def test_quadrant_meta_matches_actual(self, scored):
        """meta.quadrant_counts should match actual data."""
        actual = {}
        for s in scored["skus"]:
            q = s["quadrant"]
            actual[q] = actual.get(q, 0) + 1
        assert actual == scored["meta"]["quadrant_counts"], (
            f"Meta quadrant counts {scored['meta']['quadrant_counts']} "
            f"don't match actual {actual}"
        )

    def test_quadrants_sum_to_total(self, scored):
        """All 4 quadrant counts should sum to 50."""
        total = sum(scored["meta"]["quadrant_counts"].values())
        assert total == 50, f"Quadrant counts sum to {total}, expected 50"

    # ------------------------------------------------------------------
    # Score structure
    # ------------------------------------------------------------------

    def test_every_sku_has_required_fields(self, scored):
        required = {"sku", "product_line", "raw", "scores", "weighted_score", "quadrant"}
        for s in scored["skus"]:
            missing = required - s.keys()
            assert not missing, f"SKU {s.get('sku','?')} missing: {missing}"

    def test_every_sku_has_five_score_dimensions(self, scored):
        expected_dims = {"velocity", "contribution_margin", "shelf_space_cost",
                         "production_complexity", "cannibalization_risk"}
        for s in scored["skus"]:
            assert set(s["scores"].keys()) == expected_dims, (
                f"SKU {s['sku']} score dimensions: {set(s['scores'].keys())}"
            )

    def test_all_scores_in_1_to_5_range(self, scored):
        for s in scored["skus"]:
            for dim, val in s["scores"].items():
                assert 1 <= val <= 5, (
                    f"SKU {s['sku']} {dim}={val} out of 1-5 range"
                )
