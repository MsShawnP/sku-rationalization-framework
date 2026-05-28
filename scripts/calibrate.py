"""Calibrate scoring thresholds from actual Cinderhaven data distributions.

Queries the three new intermediate views from the Cinderhaven Postgres
(via flyctl proxy at localhost:5432) and writes percentile-based thresholds
to src/scoring/constants.py.

Requires:
  - flyctl proxy running: `flyctl proxy 5432:5432 -a cinderhaven-db`
  - POSTGRES_PASSWORD env var set (or .env in the cinderhaven-data-platform repo)

Usage:
    python scripts/calibrate.py
"""
from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

import psycopg2
import psycopg2.extras


PLATFORM_ENV = Path(__file__).parent.parent.parent.parent / "active datasources" / "cinderhaven-data-platform" / ".env"

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


PERCENTILE_SQLS = {
    "velocity": """
        SELECT
            percentile_cont(0.10) WITHIN GROUP (ORDER BY uspw) AS p10,
            percentile_cont(0.25) WITHIN GROUP (ORDER BY uspw) AS p25,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY uspw) AS p50,
            percentile_cont(0.75) WITHIN GROUP (ORDER BY uspw) AS p75,
            percentile_cont(0.90) WITHIN GROUP (ORDER BY uspw) AS p90
        FROM (
            SELECT sku, AVG(units_sold) AS uspw
            FROM raw.scan_data
            GROUP BY sku
        ) t
    """,
    "margin": """
        SELECT
            percentile_cont(0.10) WITHIN GROUP (ORDER BY loaded_margin_pct) AS p10,
            percentile_cont(0.25) WITHIN GROUP (ORDER BY loaded_margin_pct) AS p25,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY loaded_margin_pct) AS p50,
            percentile_cont(0.75) WITHIN GROUP (ORDER BY loaded_margin_pct) AS p75,
            percentile_cont(0.90) WITHIN GROUP (ORDER BY loaded_margin_pct) AS p90
        FROM public_intermediate.int_loaded_contribution_by_sku
        WHERE loaded_margin_pct IS NOT NULL
    """,
    "shelf": """
        SELECT
            percentile_cont(0.10) WITHIN GROUP (ORDER BY annual_shelf_space_cost) AS p10,
            percentile_cont(0.25) WITHIN GROUP (ORDER BY annual_shelf_space_cost) AS p25,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY annual_shelf_space_cost) AS p50,
            percentile_cont(0.75) WITHIN GROUP (ORDER BY annual_shelf_space_cost) AS p75,
            percentile_cont(0.90) WITHIN GROUP (ORDER BY annual_shelf_space_cost) AS p90
        FROM public_intermediate.int_shelf_space_cost_by_sku
    """,
    "complexity": """
        SELECT
            percentile_cont(0.10) WITHIN GROUP (ORDER BY complexity_ratio) AS p10,
            percentile_cont(0.25) WITHIN GROUP (ORDER BY complexity_ratio) AS p25,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY complexity_ratio) AS p50,
            percentile_cont(0.75) WITHIN GROUP (ORDER BY complexity_ratio) AS p75,
            percentile_cont(0.90) WITHIN GROUP (ORDER BY complexity_ratio) AS p90
        FROM (
            SELECT c.sku,
                   (c.landed_cost_per_unit / NULLIF(pm.msrp, 0)) AS complexity_ratio
            FROM raw.sku_costs c
            INNER JOIN raw.product_master pm ON c.sku = pm.sku
            WHERE pm.msrp > 0
        ) t
    """,
    "cannibalization": """
        SELECT
            percentile_cont(0.10) WITHIN GROUP (ORDER BY cannibalization_risk) AS p10,
            percentile_cont(0.25) WITHIN GROUP (ORDER BY cannibalization_risk) AS p25,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY cannibalization_risk) AS p50,
            percentile_cont(0.75) WITHIN GROUP (ORDER BY cannibalization_risk) AS p75,
            percentile_cont(0.90) WITHIN GROUP (ORDER BY cannibalization_risk) AS p90
        FROM (
            SELECT GREATEST(0, COALESCE(-velocity_delta_pct, 0)) AS cannibalization_risk
            FROM public_intermediate.int_cannibalization_pairs
            WHERE solo_stores >= 3
        ) t
    """,
}



PREFIXES = {
    "velocity": "vel",
    "margin": "margin",
    "shelf": "shelf",
    "complexity": "complex",
    "cannibalization": "cannibal",
}


def fetch_percentiles(conn: psycopg2.extensions.connection) -> dict:
    result = {}
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        for dim, sql in PERCENTILE_SQLS.items():
            print(f"  querying {dim}...", flush=True)
            cur.execute(sql)
            row = cur.fetchone()
            prefix = PREFIXES[dim]
            for pct_key, val in row.items():
                flat_key = f"{prefix}_{pct_key}"
                result[flat_key] = float(val) if val is not None else None
    return result


def render_constants(p: dict) -> str:
    return textwrap.dedent(f"""\
        # Auto-generated by scripts/calibrate.py — do not edit by hand.
        # Source: Cinderhaven Postgres percentile distributions (2024-2027 window).
        # Re-run calibrate.py against updated data before changing thresholds.

        # Scoring direction: 5 = best, 1 = worst.
        # For "lower is better" dimensions (shelf_space_cost, production_complexity,
        # cannibalization_risk), score 5 is assigned at LOW raw values.

        # --- Velocity (units/store/week) ---
        # Score 5: >= p75, Score 4: p50–p75, Score 3: p25–p50,
        # Score 2: p10–p25, Score 1: < p10
        VELOCITY_P10 = {p['vel_p10']:.4f}
        VELOCITY_P25 = {p['vel_p25']:.4f}
        VELOCITY_P50 = {p['vel_p50']:.4f}
        VELOCITY_P75 = {p['vel_p75']:.4f}
        VELOCITY_P90 = {p['vel_p90']:.4f}

        # --- Contribution margin (loaded_margin_pct, 0.0–1.0) ---
        MARGIN_P10 = {p['margin_p10']:.4f}
        MARGIN_P25 = {p['margin_p25']:.4f}
        MARGIN_P50 = {p['margin_p50']:.4f}
        MARGIN_P75 = {p['margin_p75']:.4f}
        MARGIN_P90 = {p['margin_p90']:.4f}

        # --- Shelf-space cost (annual USD) — lower is better ---
        # Score 5: ≤ p25, Score 4: p25–p50, Score 3: p50–p75,
        # Score 2: p75–p90, Score 1: > p90
        SHELF_P10 = {p['shelf_p10']:.2f}
        SHELF_P25 = {p['shelf_p25']:.2f}
        SHELF_P50 = {p['shelf_p50']:.2f}
        SHELF_P75 = {p['shelf_p75']:.2f}
        SHELF_P90 = {p['shelf_p90']:.2f}

        # --- Production complexity proxy (landed_cost/msrp ratio) — lower is better ---
        COMPLEX_P10 = {p['complex_p10']:.4f}
        COMPLEX_P25 = {p['complex_p25']:.4f}
        COMPLEX_P50 = {p['complex_p50']:.4f}
        COMPLEX_P75 = {p['complex_p75']:.4f}
        COMPLEX_P90 = {p['complex_p90']:.4f}

        # --- Cannibalization risk (inverted velocity delta) — lower is better ---
        # 0.0 = no signal, positive = velocity drops in shared stores
        CANNIBAL_P10 = {p['cannibal_p10']:.4f}
        CANNIBAL_P25 = {p['cannibal_p25']:.4f}
        CANNIBAL_P50 = {p['cannibal_p50']:.4f}
        CANNIBAL_P75 = {p['cannibal_p75']:.4f}
        CANNIBAL_P90 = {p['cannibal_p90']:.4f}
    """)


def main() -> None:
    print("Connecting to Cinderhaven Postgres via proxy...")
    try:
        conn = connect()
    except psycopg2.OperationalError as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        print("Is `flyctl proxy 5432:5432 -a cinderhaven-db` running?", file=sys.stderr)
        sys.exit(1)

    print("Querying percentile distributions...")
    p = fetch_percentiles(conn)
    conn.close()

    print("Percentile results:")
    for key, val in p.items():
        print(f"  {key}: {val:.4f}" if val is not None else f"  {key}: None")

    out_path = Path(__file__).parent.parent / "src" / "scoring" / "constants.py"
    out_path.write_text(render_constants(p), encoding="utf-8")
    print(f"\nThresholds written to {out_path}")


if __name__ == "__main__":
    main()
