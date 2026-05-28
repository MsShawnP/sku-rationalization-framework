"""Tests for quadrant assignment and weighted composite score."""

import pytest
from src.scoring.quadrants import assign_quadrant, compute_weighted_score

# Hand-verified fixtures: (velocity, contribution_margin, shelf_space_cost,
#                           production_complexity, cannibalization_risk) -> quadrant
FIXTURES = [
    # FIXTURE-001: all 5s — no red flags, min >= 4 → double_down
    ({"velocity": 5, "contribution_margin": 5, "shelf_space_cost": 5,
      "production_complexity": 5, "cannibalization_risk": 5}, "double_down"),
    # FIXTURE-002: all 1s — 5 red flags → kill
    ({"velocity": 1, "contribution_margin": 1, "shelf_space_cost": 1,
      "production_complexity": 1, "cannibalization_risk": 1}, "kill"),
    # FIXTURE-003: all 4s — no red flags, min >= 4 → double_down
    ({"velocity": 4, "contribution_margin": 4, "shelf_space_cost": 4,
      "production_complexity": 4, "cannibalization_risk": 4}, "double_down"),
    # FIXTURE-004: all 3s — no red flags, min < 4 → maintain
    ({"velocity": 3, "contribution_margin": 3, "shelf_space_cost": 3,
      "production_complexity": 3, "cannibalization_risk": 3}, "maintain"),
    # FIXTURE-005: all 2s — 5 red flags → kill
    ({"velocity": 2, "contribution_margin": 2, "shelf_space_cost": 2,
      "production_complexity": 2, "cannibalization_risk": 2}, "kill"),
    # FIXTURE-006: one 1, rest 3s — exactly 1 red flag → fix_or_kill
    ({"velocity": 1, "contribution_margin": 3, "shelf_space_cost": 3,
      "production_complexity": 3, "cannibalization_risk": 3}, "fix_or_kill"),
    # FIXTURE-007: one 2, rest 3s — exactly 1 red flag → fix_or_kill
    ({"velocity": 3, "contribution_margin": 2, "shelf_space_cost": 3,
      "production_complexity": 3, "cannibalization_risk": 3}, "fix_or_kill"),
    # FIXTURE-008: two 1s, rest 3s — 2 red flags → kill
    ({"velocity": 1, "contribution_margin": 1, "shelf_space_cost": 3,
      "production_complexity": 3, "cannibalization_risk": 3}, "kill"),
    # FIXTURE-009: one 4, rest 3s — no red flags, min < 4 → maintain
    ({"velocity": 4, "contribution_margin": 3, "shelf_space_cost": 3,
      "production_complexity": 3, "cannibalization_risk": 3}, "maintain"),
    # FIXTURE-010: one 5, rest 4s — no red flags, min >= 4 → double_down
    ({"velocity": 5, "contribution_margin": 4, "shelf_space_cost": 4,
      "production_complexity": 4, "cannibalization_risk": 4}, "double_down"),
    # FIXTURE-011: two 2s (boundary), rest 3s — exactly 2 red flags → kill
    ({"velocity": 2, "contribution_margin": 2, "shelf_space_cost": 3,
      "production_complexity": 3, "cannibalization_risk": 3}, "kill"),
    # FIXTURE-012: mix 5,4,3,2,3 — exactly 1 red flag → fix_or_kill
    ({"velocity": 5, "contribution_margin": 4, "shelf_space_cost": 3,
      "production_complexity": 2, "cannibalization_risk": 3}, "fix_or_kill"),
]


@pytest.mark.parametrize("scores,expected", FIXTURES)
def test_assign_quadrant(scores, expected):
    assert assign_quadrant(scores) == expected


def test_weighted_score_equal_weights_all_fives():
    scores = {d: 5 for d in ["velocity", "contribution_margin",
                              "shelf_space_cost", "production_complexity",
                              "cannibalization_risk"]}
    assert compute_weighted_score(scores) == 5.0


def test_weighted_score_equal_weights_all_ones():
    scores = {d: 1 for d in ["velocity", "contribution_margin",
                              "shelf_space_cost", "production_complexity",
                              "cannibalization_risk"]}
    assert compute_weighted_score(scores) == 1.0


def test_weighted_score_custom_weights():
    scores = {"velocity": 5, "contribution_margin": 1,
              "shelf_space_cost": 1, "production_complexity": 1,
              "cannibalization_risk": 1}
    weights = {"velocity": 0.60, "contribution_margin": 0.10,
               "shelf_space_cost": 0.10, "production_complexity": 0.10,
               "cannibalization_risk": 0.10}
    # 5*0.6 + 1*0.1 + 1*0.1 + 1*0.1 + 1*0.1 = 3.0 + 0.4 = 3.4
    assert compute_weighted_score(scores, weights) == pytest.approx(3.4, abs=1e-4)


def test_weighted_score_mixed():
    scores = {"velocity": 3, "contribution_margin": 3, "shelf_space_cost": 3,
              "production_complexity": 3, "cannibalization_risk": 3}
    assert compute_weighted_score(scores) == pytest.approx(3.0, abs=1e-4)
