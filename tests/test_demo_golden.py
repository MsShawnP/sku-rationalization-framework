"""Demo golden lock — sku-rationalization-framework.

Byte-locks the committed scored dataset (data/cinderhaven_scored.json) the app
renders, and pins the SKU count + quadrant distribution + a sample scored SKU.
If a SHA or a figure moves, STOP: a golden moved.
"""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCORED = ROOT / "data" / "cinderhaven_scored.json"

GOLDEN_SHA256_PREFIX = "ec755c95a3f23e6d"


@pytest.fixture(scope="module")
def scored():
    return json.loads(SCORED.read_text())


def test_scored_json_sha256():
    digest = hashlib.sha256(SCORED.read_bytes()).hexdigest()[:16]
    assert digest == GOLDEN_SHA256_PREFIX, (
        f"cinderhaven_scored.json changed (sha256[:16] {digest} != golden "
        f"{GOLDEN_SHA256_PREFIX}) — a demo golden moved; STOP and report."
    )


def test_sku_count(scored):
    assert scored["meta"]["sku_count"] == 50
    assert len(scored["skus"]) == 50


def test_quadrant_distribution(scored):
    counts = dict(collections.Counter(s["quadrant"] for s in scored["skus"]))
    assert counts == {"fix_or_kill": 14, "kill": 19, "maintain": 16, "double_down": 1}
    assert scored["meta"]["quadrant_counts"] == counts


def test_scoring_reproduces_a_sample_sku(scored):
    # The scoring engine reproduces a committed SKU's quadrant from its raw
    # dimensions — the demo output is a faithful product of the engine.
    from src.scoring.engine import score_sku
    sample = next(s for s in scored["skus"] if s["sku"] == "CHP-AS-001")
    r = sample["raw"]
    rescored = score_sku(
        sample["sku"], sample["product_line"], r["uspw"], r["loaded_margin_pct"],
        r["annual_shelf_space_cost"], r["complexity_ratio"], r["cannibalization_risk"],
    )
    assert rescored["quadrant"] == sample["quadrant"]
    assert rescored["scores"] == sample["scores"]
    assert rescored["weighted_score"] == sample["weighted_score"]
