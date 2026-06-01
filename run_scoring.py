"""Score all Cinderhaven SKUs and write data/cinderhaven_scored.json.

Requires:
  - flyctl proxy running: `flyctl proxy 5432:5432 -a cinderhaven-db`
  - POSTGRES_PASSWORD env var set (or .env in the cinderhaven-data-platform repo)

Usage:
    python run_scoring.py
    python run_scoring.py --weights vel=0.4,margin=0.3,shelf=0.1,complexity=0.1,cannibal=0.1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

from src.scoring.db import connect
from src.scoring.engine import score_sku
from src.scoring.quadrants import DEFAULT_WEIGHTS

_WEIGHT_ALIASES: dict[str, str] = {
    'vel':                    'velocity',
    'velocity':               'velocity',
    'margin':                 'contribution_margin',
    'contribution_margin':    'contribution_margin',
    'shelf':                  'shelf_space_cost',
    'shelf_space_cost':       'shelf_space_cost',
    'complexity':             'production_complexity',
    'production_complexity':  'production_complexity',
    'cannibal':               'cannibalization_risk',
    'cannibalization_risk':   'cannibalization_risk',
}


def parse_weights(raw: str) -> dict[str, float]:
    """Parse 'vel=0.4,margin=0.3,...' into a normalized full-key weights dict.

    Missing dimensions receive an equal share of the remaining weight.
    Values are always normalized to sum exactly to 1.0.
    """
    all_dims = list(DEFAULT_WEIGHTS)
    parsed: dict[str, float] = {}
    for part in (p.strip() for p in raw.split(',') if p.strip()):
        if '=' not in part:
            raise SystemExit(f"Invalid weight spec {part!r} — use key=value (e.g. vel=0.4)")
        key, _, val_str = part.partition('=')
        key = key.strip()
        if key not in _WEIGHT_ALIASES:
            valid = ', '.join(sorted({k for k in _WEIGHT_ALIASES if k == _WEIGHT_ALIASES[k] or len(k) < 10}))
            raise SystemExit(f"Unknown weight key {key!r}. Valid short keys: vel, margin, shelf, complexity, cannibal")
        try:
            val = float(val_str)
        except ValueError:
            raise SystemExit(f"Weight value for {key!r} must be a number, got {val_str!r}")
        parsed[_WEIGHT_ALIASES[key]] = val

    missing = [d for d in all_dims if d not in parsed]
    specified_total = sum(parsed.values())
    if missing:
        remaining = max(0.0, 1.0 - specified_total)
        share = remaining / len(missing) if remaining > 0 else 0.0
        for d in missing:
            parsed[d] = share

    total = sum(parsed.values())
    if total <= 0:
        raise SystemExit("Weights sum to zero — at least one dimension must have a positive weight")
    return {d: parsed[d] / total for d in all_dims}

_DEFAULT_ENV = (
    Path(__file__).parent.parent.parent
    / "active datasources"
    / "cinderhaven-data-platform"
    / ".env"
)
PLATFORM_ENV = Path(os.environ["CINDERHAVEN_ENV"]) if "CINDERHAVEN_ENV" in os.environ else _DEFAULT_ENV

QUERY = """
SELECT
    pm.sku,
    pm.product_line,
    v.uspw,
    m.loaded_margin_pct,
    s.annual_shelf_space_cost,
    (sc.landed_cost_per_unit / NULLIF(pm.msrp, 0)) AS complexity_ratio,
    c.cannibalization_risk
FROM raw.product_master pm
LEFT JOIN (
    SELECT sku, AVG(units_sold) AS uspw
    FROM raw.scan_data
    GROUP BY sku
) v ON pm.sku = v.sku
LEFT JOIN (
    SELECT sku, loaded_margin_pct
    FROM public_intermediate.int_loaded_contribution_by_sku
) m ON pm.sku = m.sku
LEFT JOIN (
    SELECT sku, annual_shelf_space_cost
    FROM public_intermediate.int_shelf_space_cost_by_sku
) s ON pm.sku = s.sku
LEFT JOIN raw.sku_costs sc ON pm.sku = sc.sku
LEFT JOIN (
    SELECT sku,
           GREATEST(0, COALESCE(-velocity_delta_pct, 0)) AS cannibalization_risk
    FROM public_intermediate.int_cannibalization_pairs
    WHERE solo_stores >= 3
) c ON pm.sku = c.sku
ORDER BY pm.product_line, pm.sku
"""




def fetch_raw_skus(conn: psycopg2.extensions.connection) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(QUERY)
        return [dict(row) for row in cur.fetchall()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Score Cinderhaven SKUs and write data/cinderhaven_scored.json")
    parser.add_argument(
        '--weights',
        metavar='KEY=VAL,...',
        default=None,
        help=(
            'Custom scoring weights. Example: --weights vel=0.4,margin=0.3,shelf=0.1,complexity=0.1,cannibal=0.1. '
            'Missing dimensions share the remaining weight equally. Values are normalized to sum to 1.'
        ),
    )
    args = parser.parse_args()

    custom_weights: dict[str, float] | None = None
    if args.weights:
        custom_weights = parse_weights(args.weights)
        print("Custom weights:")
        for dim, w in custom_weights.items():
            print(f"  {dim}: {w:.1%}")

    print("Connecting to Cinderhaven Postgres via proxy...")
    try:
        conn = connect(PLATFORM_ENV)
    except psycopg2.OperationalError as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        print("Is `flyctl proxy 5432:5432 -a cinderhaven-db` running?", file=sys.stderr)
        sys.exit(1)

    print("Fetching raw SKU data...")
    rows = fetch_raw_skus(conn)
    conn.close()
    _required = ("uspw", "loaded_margin_pct", "annual_shelf_space_cost", "complexity_ratio")
    partial_count = sum(1 for r in rows if any(r[k] is None for k in _required))
    print(f"  {len(rows)} SKUs retrieved ({partial_count} with at least one missing dimension)")

    print("Scoring SKUs...")
    scored = []
    for row in rows:
        result = score_sku(
            sku=row["sku"],
            product_line=row["product_line"],
            uspw=float(row["uspw"]) if row["uspw"] is not None else None,
            loaded_margin_pct=float(row["loaded_margin_pct"]) if row["loaded_margin_pct"] is not None else None,
            annual_shelf_space_cost=float(row["annual_shelf_space_cost"]) if row["annual_shelf_space_cost"] is not None else None,
            complexity_ratio=float(row["complexity_ratio"]) if row["complexity_ratio"] is not None else None,
            cannibalization_risk=(
                float(row["cannibalization_risk"])
                if row["cannibalization_risk"] is not None
                else None
            ),
            weights=custom_weights,
        )
        scored.append(result)

    quadrant_counts: dict[str, int] = {}
    for s in scored:
        q = s["quadrant"]
        quadrant_counts[q] = quadrant_counts.get(q, 0) + 1
    print("  Quadrant distribution:", quadrant_counts)

    output = {
        "meta": {
            "source": "Cinderhaven Postgres (2024-2027 window)",
            "scoring_version": "v1",
            "sku_count": len(scored),
            "quadrant_counts": quadrant_counts,
            "weights": custom_weights if custom_weights is not None else DEFAULT_WEIGHTS,
            "methodology_note": (
                "Cannibalization scored via proxy (cross-sectional velocity comparison). "
                "All margins negative after full cost loading — scoring is portfolio-relative."
            ),
        },
        "skus": scored,
    }

    out_path = Path(__file__).parent / "data" / "cinderhaven_scored.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nScored data written to {out_path}")


if __name__ == "__main__":
    main()
