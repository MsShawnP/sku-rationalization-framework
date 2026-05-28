"""Score all Cinderhaven SKUs and write data/cinderhaven_scored.json.

Requires:
  - flyctl proxy running: `flyctl proxy 5432:5432 -a cinderhaven-db`
  - POSTGRES_PASSWORD env var set (or .env in the cinderhaven-data-platform repo)

Usage:
    python run_scoring.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

from src.scoring.engine import score_sku

PLATFORM_ENV = (
    Path(__file__).parent.parent.parent
    / "active datasources"
    / "cinderhaven-data-platform"
    / ".env"
)

QUERY = """
SELECT
    v.sku,
    pm.product_line,
    v.uspw,
    m.loaded_margin_pct,
    s.annual_shelf_space_cost,
    cp.complexity_ratio,
    c.cannibalization_risk
FROM (
    SELECT sku, AVG(units_sold) AS uspw
    FROM raw.scan_data
    GROUP BY sku
) v
JOIN (
    SELECT sku, product_line
    FROM raw.product_master
) pm ON v.sku = pm.sku
JOIN (
    SELECT sku, loaded_margin_pct
    FROM public_intermediate.int_loaded_contribution_by_sku
) m ON v.sku = m.sku
JOIN (
    SELECT s.sku, s.annual_shelf_space_cost
    FROM public_intermediate.int_shelf_space_cost_by_sku s
) s ON v.sku = s.sku
JOIN (
    SELECT c.sku,
           (c.landed_cost_per_unit / NULLIF(pm2.msrp, 0)) AS complexity_ratio
    FROM raw.sku_costs c
    INNER JOIN raw.product_master pm2 ON c.sku = pm2.sku
    WHERE pm2.msrp > 0
) cp ON v.sku = cp.sku
LEFT JOIN (
    SELECT sku,
           GREATEST(0, COALESCE(-velocity_delta_pct, 0)) AS cannibalization_risk
    FROM public_intermediate.int_cannibalization_pairs
    WHERE solo_stores >= 3
) c ON v.sku = c.sku
ORDER BY pm.product_line, v.sku
"""


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def connect() -> psycopg2.extensions.connection:
    load_env(PLATFORM_ENV)
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="cinderhaven",
        user="postgres",
        password=os.environ["POSTGRES_PASSWORD"],
    )


def fetch_raw_skus(conn: psycopg2.extensions.connection) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(QUERY)
        return [dict(row) for row in cur.fetchall()]


def main() -> None:
    print("Connecting to Cinderhaven Postgres via proxy...")
    try:
        conn = connect()
    except psycopg2.OperationalError as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        print("Is `flyctl proxy 5432:5432 -a cinderhaven-db` running?", file=sys.stderr)
        sys.exit(1)

    print("Fetching raw SKU data...")
    rows = fetch_raw_skus(conn)
    conn.close()
    print(f"  {len(rows)} SKUs retrieved")

    print("Scoring SKUs...")
    scored = []
    for row in rows:
        result = score_sku(
            sku=row["sku"],
            product_line=row["product_line"],
            uspw=float(row["uspw"]),
            loaded_margin_pct=float(row["loaded_margin_pct"]),
            annual_shelf_space_cost=float(row["annual_shelf_space_cost"]),
            complexity_ratio=float(row["complexity_ratio"]),
            cannibalization_risk=(
                float(row["cannibalization_risk"])
                if row["cannibalization_risk"] is not None
                else None
            ),
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
