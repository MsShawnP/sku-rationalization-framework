"""Client-mode CLI for sku-rationalization-framework.

Scores a client's SKU portfolio with the same engine the demo uses (score_sku)
and produces a branded quadrant deliverable — validated, never committed, never
deployed. The demo app + committed scored dataset are untouched.

Usage:
    python client_mode.py --config engagement.yml --input client-data/skus.csv \
        --out client-output [--final]
"""

from __future__ import annotations

import argparse
import collections
import html
import json
import sys
from pathlib import Path

from lailara_engagement import (
    ColumnSpec,
    PreflightSpec,
    build_provenance,
    load_config,
    read_table,
    run_preflight,
    validation_status_label,
    write_report,
)
from lailara_engagement import palette as P
from lailara_engagement.provenance import Provenance

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.scoring.engine import score_sku  # noqa: E402

TOOL = "sku-rationalization-framework"
TOOL_VERSION = "1.0"

QUADRANT_LABELS = {
    "double_down": "Double down", "maintain": "Maintain",
    "fix_or_kill": "Fix or kill", "kill": "Kill",
    "insufficient_data": "Insufficient data",
}


def _spec() -> PreflightSpec:
    return PreflightSpec(
        tool=TOOL, version=TOOL_VERSION,
        columns=[
            ColumnSpec(name="sku", dtype="identifier", required=True, unique=True,
                       description="SKU code", spec_ref="INPUT-SPEC §1"),
            ColumnSpec(name="product_line", dtype="string", required=True,
                       description="product line", spec_ref="INPUT-SPEC §1"),
            # Scoring dimensions — allow_blank: a blank leaves that dimension
            # unscored (score_sku accepts None); a SKU missing too much data is
            # classified "insufficient_data", never guessed.
            ColumnSpec(name="uspw", dtype="number", required=False, allow_blank=True,
                       description="units per store per week (velocity)"),
            ColumnSpec(name="loaded_margin_pct", dtype="number", required=False, allow_blank=True,
                       description="loaded contribution margin rate"),
            ColumnSpec(name="annual_shelf_space_cost", dtype="number", required=False, allow_blank=True,
                       not_negative=True, description="annual shelf-space cost"),
            ColumnSpec(name="complexity_ratio", dtype="number", required=False, allow_blank=True,
                       not_negative=True, description="production complexity ratio"),
            ColumnSpec(name="cannibalization_risk", dtype="number", required=False, allow_blank=True,
                       description="cannibalization risk (0..1); blank -> 0"),
        ],
    )


def _fnum(v):
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def run(config_path: str, input_path: str, out_dir: str, *, final: bool = False) -> dict:
    config = load_config(config_path)
    read = read_table(input_path)
    report = run_preflight(read, _spec(), config)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    provenance = build_provenance(
        tool=TOOL, tool_version=TOOL_VERSION, inputs=[read], config=config,
        validation_status=validation_status_label(report.status, report.n_warnings))
    if not report.passed:
        paths = write_report(report, config, str(out), provenance=provenance,
                             draft=not final, basename="data-readiness-report",
                             title="SKU Rationalization Data Readiness Report")
        return {"status": "blocked", "readiness_report": paths["html"]}

    m = report.column_mapping
    frame = read.frame
    weights = config.basis.get("weights") if isinstance(config.basis.get("weights"), dict) else None

    def col(name):
        r = m.get(name)
        return frame[r] if r else None

    scored = []
    for i in range(len(frame)):
        rec = score_sku(
            sku=str(col("sku").iloc[i]).strip(),
            product_line=str(col("product_line").iloc[i]).strip() if col("product_line") is not None else "",
            uspw=_fnum(col("uspw").iloc[i]) if col("uspw") is not None else None,
            loaded_margin_pct=_fnum(col("loaded_margin_pct").iloc[i]) if col("loaded_margin_pct") is not None else None,
            annual_shelf_space_cost=_fnum(col("annual_shelf_space_cost").iloc[i]) if col("annual_shelf_space_cost") is not None else None,
            complexity_ratio=_fnum(col("complexity_ratio").iloc[i]) if col("complexity_ratio") is not None else None,
            cannibalization_risk=_fnum(col("cannibalization_risk").iloc[i]) if col("cannibalization_risk") is not None else None,
            weights=weights,
        )
        scored.append(rec)

    counts = dict(collections.Counter(r["quadrant"] for r in scored))
    summary = {
        "window": {"label": config.basis.get("window_label", "")},
        "sku_count": len(scored),
        "quadrant_counts": counts,
        "skus": [{"sku": r["sku"], "product_line": r["product_line"],
                  "quadrant": r["quadrant"], "weighted_score": r["weighted_score"],
                  "scores": r["scores"]} for r in scored],
        "weights": (weights or scored[0]["weights_used"]) if scored else weights,
    }
    json_dir = out / "json"; json_dir.mkdir(parents=True, exist_ok=True)
    (json_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path = out / "sku-rationalization-summary.html"
    report_path.write_text(_summary_html(config, summary, provenance, draft=not final), encoding="utf-8")
    insufficient = counts.get("insufficient_data", 0)
    return {"status": "ok", "sku_count": len(scored), "quadrant_counts": counts,
            "insufficient": insufficient, "report": str(report_path),
            "summary_json": str(json_dir / "summary.json"), "n_warnings": report.n_warnings}


def _summary_html(config, s, provenance: Provenance, *, draft: bool) -> str:
    esc = html.escape
    wl = s["window"].get("label") or ""
    order = ["double_down", "maintain", "fix_or_kill", "kill", "insufficient_data"]
    q_rows = "".join(
        f"<tr><td>{esc(QUADRANT_LABELS.get(q, q))}</td><td class=num>{s['quadrant_counts'].get(q, 0)}</td></tr>"
        for q in order if s["quadrant_counts"].get(q, 0))

    def _sku_row(r):
        ws = "—" if r["weighted_score"] is None else round(r["weighted_score"], 2)
        return (f"<tr><td>{esc(r['sku'])}</td><td>{esc(r['product_line'])}</td>"
                f"<td>{esc(QUADRANT_LABELS.get(r['quadrant'], r['quadrant']))}</td>"
                f"<td class=num>{ws}</td></tr>")

    sku_rows = "".join(_sku_row(r) for r in s["skus"])
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>SKU Rationalization — {esc(config.client_name)}</title><style>{_css(draft)}</style></head>
<body class="{' ll-draft' if draft else ''}"><main class=ll-page>
<header class=ll-header>
  <div class=ll-eyebrow>Lailara LLC · SKU Rationalization</div>
  <h1 class=ll-title>Portfolio by Quadrant</h1>
  <div class=ll-client>
    <div><span class=ll-k>Client</span> {esc(config.client_name)}</div>
    <div><span class=ll-k>Engagement</span> {esc(config.engagement_id)}</div>
    <div><span class=ll-k>As of</span> {esc(config.as_of_date.isoformat())}</div>
    <div><span class=ll-k>Window</span> {esc(wl) or '—'}</div>
  </div>
</header>
<section class=ll-banner>
  <div class=ll-score>{s['sku_count']} SKUs scored</div>
  <div>across five weighted dimensions (velocity, loaded margin, shelf cost,
       complexity, cannibalization)</div>
</section>
<section class=ll-section>
  <h2 class=ll-h2>Quadrant distribution</h2>
  <table class=ll-table><thead><tr><th>Quadrant</th><th>SKUs</th></tr></thead><tbody>{q_rows}</tbody></table>
</section>
<section class=ll-section>
  <h2 class=ll-h2>By SKU</h2>
  <table class=ll-table><thead><tr><th>SKU</th><th>Product line</th><th>Quadrant</th>
  <th>Weighted score</th></tr></thead><tbody>{sku_rows}</tbody></table>
  <p class=ll-note>Weighted score = mean of the five dimension scores (0–5) under the
  configured weights. SKUs missing too many dimensions are classed "Insufficient data",
  never guessed.</p>
</section>
{provenance.to_html()}
</main></body></html>"""


def _css(draft: bool) -> str:
    draft_css = (
        ".ll-draft::before{content:'DRAFT';position:fixed;top:50%;left:50%;"
        "transform:translate(-50%,-50%) rotate(-32deg);font-family:var(--s);"
        "font-size:22vw;font-weight:700;color:rgba(204,16,10,.06);z-index:0;"
        "pointer-events:none;white-space:nowrap}" if draft else ""
    )
    return f"""
:root{{--s:{P.LL_SERIF};--f:{P.LL_SANS}}}*{{box-sizing:border-box}}
body{{margin:0;background:{P.LL_CANVAS};color:{P.LL_TEXT};font-family:var(--f);line-height:1.6}}
.ll-page{{position:relative;z-index:1;max-width:{P.LL_MAX_WIDTH};margin:0 auto;padding:48px 24px}}
.ll-header{{border-bottom:1px solid {P.LL_GRIDLINE};padding-bottom:24px;margin-bottom:24px}}
.ll-eyebrow{{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:{P.LL_RED};font-weight:600}}
.ll-title{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:34px;margin:8px 0 16px}}
.ll-client{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px 24px;font-size:14px}}
.ll-k{{display:block;color:{P.LL_TEXT_SEC};font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
.ll-banner{{border-radius:2px;padding:16px 20px;margin-bottom:32px;background:{P.LL_HK_SURFACE};color:{P.LL_HK_DARK}}}
.ll-score{{font-family:var(--s);font-weight:700;font-size:22px}}
.ll-section{{margin:0 0 32px}}
.ll-h2{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:22px;
margin:0 0 12px;padding-bottom:6px;border-bottom:1px solid {P.LL_GRIDLINE}}}
.ll-note{{font-size:13px;color:{P.LL_TEXT_SEC};margin-top:8px}}
.ll-table{{width:100%;border-collapse:collapse;font-size:14px}}
.ll-table th{{text-align:left;background:{P.LL_CHICAGO};color:#fff;padding:8px 12px}}
.ll-table td{{padding:8px 12px;border-bottom:1px solid {P.LL_GRIDLINE}}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.ll-provenance{{margin-top:40px;background:{P.LL_CARD_BG};color:{P.LL_CARD_TEXT};
padding:20px 24px;border-radius:2px;font-size:13px}}
.ll-prov-title{{font-family:var(--s);font-weight:700;font-size:16px;margin-bottom:8px}}
.ll-provenance div{{margin-bottom:4px;color:{P.LL_CARD_SUBTITLE}}}
.ll-provenance strong{{color:{P.LL_CARD_TEXT}}}
.ll-prov-inputs{{width:100%;border-collapse:collapse;margin-top:8px}}
.ll-prov-inputs th{{text-align:left;border-bottom:1px solid rgba(255,255,255,.12);padding:4px 8px;color:{P.LL_CARD_MUTED}}}
.ll-prov-inputs td{{padding:4px 8px;border-bottom:1px solid rgba(255,255,255,.08);color:{P.LL_CARD_SUBTITLE}}}
.ll-prov-brand{{margin-top:12px;font-family:var(--s);color:{P.LL_CARD_MUTED}}}
{draft_css}
@media print{{body{{background:#fff}}}}
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sku-rationalization client mode")
    ap.add_argument("--config", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default="client-output")
    ap.add_argument("--final", action="store_true")
    args = ap.parse_args(argv)
    result = run(args.config, args.input, args.out, final=args.final)
    if result["status"] == "blocked":
        print(f"BLOCKED — data not ready. See {result['readiness_report']}")
        return 3
    print(f"scored {result['sku_count']} SKUs: {result['quadrant_counts']}")
    print(f"report -> {result['report']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
