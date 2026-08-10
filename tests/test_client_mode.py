"""Client-mode tests for sku-rationalization-framework.

Adversarial fixtures per checklist §6: clean run (uses the real scoring engine),
insufficient-data SKU (missing dimensions -> classified, not guessed), missing
required column (blocked), duplicate SKU, empty file, --final watermark.
Fictional-placeholder identity.

Skipped if lailara_engagement isn't installed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("lailara_engagement")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import client_mode  # noqa: E402

from lailara_engagement.errors import ReadError  # noqa: E402

_CONFIG = """
client: {name: Meridian Farms}
engagement: {id: MER-2026-08}
as_of_date: "2026-01-31"
demo: true
basis: {window_label: "2023-2026"}
columns:
  sku: sku
  product_line: product_line
  uspw: uspw
  loaded_margin_pct: loaded_margin_pct
  annual_shelf_space_cost: annual_shelf_space_cost
  complexity_ratio: complexity_ratio
  cannibalization_risk: cannibalization_risk
"""

_CLEAN = (
    "sku,product_line,uspw,loaded_margin_pct,annual_shelf_space_cost,complexity_ratio,cannibalization_risk\n"
    "MF-001,Sauces,16.5,-4.37,157021.89,0.29,0.0\n"
    "MF-002,Snacks,2.1,-9.80,240000.00,0.85,0.6\n"
)


def _cfg(tmp_path):
    p = tmp_path / "engagement.yml"
    p.write_text(_CONFIG, encoding="utf-8")
    return str(p)


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_clean_run_scores_via_engine(tmp_path):
    src = _write(tmp_path, "s.csv", _CLEAN)
    result = client_mode.run(_cfg(tmp_path), src, str(tmp_path / "out"))
    assert result["status"] == "ok"
    assert result["sku_count"] == 2
    s = json.load(open(result["summary_json"], encoding="utf-8"))
    # each SKU gets a quadrant + five dimension scores from the real engine
    for r in s["skus"]:
        assert r["quadrant"] in ("double_down", "maintain", "fix_or_kill", "kill", "insufficient_data")
        assert set(r["scores"]) == {"velocity", "contribution_margin", "shelf_space_cost",
                                    "production_complexity", "cannibalization_risk"}
    html = open(result["report"], encoding="utf-8").read()
    assert "Meridian Farms" in html and "SHA-256" in html and "DRAFT" in html


def test_window_label_tracks_config_not_hardcoded(tmp_path):
    """The rendered window label must be basis.window_label verbatim, not a
    hardcoded default. The suite asserted quadrant/scoring output but never the
    window text — a hardcoded window matching the demo would pass, the gap that
    let trade-spend quote 26 weeks as 'trailing 52 weeks'.

    Both halves: feed a distinctive window_label and assert it renders, AND
    assert the demo default is absent (a hardcode can't produce the distinctive
    value)."""
    cfg = tmp_path / "engagement.yml"
    cfg.write_text(_CONFIG.replace('window_label: "2023-2026"', 'window_label: "FY-pilot-9x"'),
                   encoding="utf-8")
    src = _write(tmp_path, "s.csv", _CLEAN)
    result = client_mode.run(str(cfg), src, str(tmp_path / "out"))
    assert result["status"] == "ok"
    html = open(result["report"], encoding="utf-8").read()
    assert "FY-pilot-9x" in html
    assert "2023-2026" not in html                    # demo default must not survive


def test_insufficient_data_classified_not_guessed(tmp_path):
    # A SKU with all scoring dimensions blank is classified insufficient_data,
    # not scored with invented numbers.
    body = ("sku,product_line,uspw,loaded_margin_pct,annual_shelf_space_cost,complexity_ratio,cannibalization_risk\n"
            "MF-009,Mystery,,,,,\n")
    src = _write(tmp_path, "i.csv", body)
    result = client_mode.run(_cfg(tmp_path), src, str(tmp_path / "out"))
    assert result["status"] == "ok"
    s = json.load(open(result["summary_json"], encoding="utf-8"))
    assert s["skus"][0]["quadrant"] == "insufficient_data"


def test_missing_required_column_blocks(tmp_path):
    src = _write(tmp_path, "bad.csv", "sku,uspw\nMF-1,10\n")   # no product_line
    result = client_mode.run(_cfg(tmp_path), src, str(tmp_path / "out"))
    assert result["status"] == "blocked"
    assert "product_line" in open(result["readiness_report"], encoding="utf-8").read().lower()


def test_duplicate_sku_blocks(tmp_path):
    body = ("sku,product_line,uspw,loaded_margin_pct,annual_shelf_space_cost,complexity_ratio,cannibalization_risk\n"
            "MF-1,Sauces,10,-4,100000,0.3,0\nMF-1,Snacks,5,-6,120000,0.4,0.1\n")
    src = _write(tmp_path, "dup.csv", body)
    result = client_mode.run(_cfg(tmp_path), src, str(tmp_path / "out"))
    assert result["status"] == "blocked"
    assert "duplicat" in open(result["readiness_report"], encoding="utf-8").read().lower()


def test_empty_file_raises(tmp_path):
    src = _write(tmp_path, "e.csv", "")
    with pytest.raises(ReadError):
        client_mode.run(_cfg(tmp_path), src, str(tmp_path / "out"))


def test_final_drops_watermark(tmp_path):
    src = _write(tmp_path, "s.csv", _CLEAN)
    result = client_mode.run(_cfg(tmp_path), src, str(tmp_path / "out"), final=True)
    assert "ll-draft" not in open(result["report"], encoding="utf-8").read()
