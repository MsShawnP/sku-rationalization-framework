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
import re
import sys
import textwrap
from pathlib import Path

import psycopg2
import psycopg2.extras

# Allow running as `python scripts/calibrate.py` from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.scoring.db import connect, load_env  # noqa: E402

_DEFAULT_ENV = Path(__file__).parent.parent.parent.parent / "active datasources" / "cinderhaven-data-platform" / ".env"
PLATFORM_ENV = Path(os.environ["CINDERHAVEN_ENV"]) if "CINDERHAVEN_ENV" in os.environ else _DEFAULT_ENV


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


def validate_percentiles(p: dict) -> None:
    """Raise ValueError if any percentile value is None (NULL from DB).

    A NULL means the query returned no rows for that distribution — most
    likely an empty table or a filter that excluded all rows. Fail before
    any file write rather than generating a broken constants.py.
    """
    nulls = [key for key, val in p.items() if val is None]
    if nulls:
        raise ValueError(
            f"Percentile query returned NULL for: {', '.join(nulls)}. "
            "Check that the source tables are populated and the WHERE clauses "
            "are not excluding all rows."
        )


def sync_sql_thresholds(p: dict, sql_path: Path) -> None:
    """Update hardcoded scoring thresholds in diagnostic_queries.sql.

    Rewrites threshold values in:
      - Query 2: CASE WHEN ... THEN 1-5 scored blocks
      - Query 3: inline CASE WHEN ... THEN 0/1 red-flag blocks

    Uses targeted regex so surrounding SQL formatting is preserved.
    Called after validate_percentiles() so no None values reach formatting.
    """
    sql = sql_path.read_text(encoding="utf-8")

    def sub(pattern: str, repl: str) -> None:
        nonlocal sql
        sql = re.sub(pattern, repl, sql)

    # Q2: velocity thresholds — THEN [5/4/3/2] discriminates each tier
    sub(r'(WHEN v\.uspw >= )([\d.]+)( THEN 5)', fr'\g<1>{p["vel_p75"]:.4f}\g<3>')
    sub(r'(WHEN v\.uspw >= )([\d.]+)( THEN 4)', fr'\g<1>{p["vel_p50"]:.4f}\g<3>')
    sub(r'(WHEN v\.uspw >= )([\d.]+)( THEN 3)', fr'\g<1>{p["vel_p25"]:.4f}\g<3>')
    sub(r'(WHEN v\.uspw >= )([\d.]+)( THEN 2)', fr'\g<1>{p["vel_p10"]:.4f}\g<3>')

    # Q2: margin thresholds — handle negative values with -? prefix
    sub(r'(WHEN m\.loaded_margin_pct >= )(-?[\d.]+)( THEN 5)', fr'\g<1>{p["margin_p75"]:.4f}\g<3>')
    sub(r'(WHEN m\.loaded_margin_pct >= )(-?[\d.]+)( THEN 4)', fr'\g<1>{p["margin_p50"]:.4f}\g<3>')
    sub(r'(WHEN m\.loaded_margin_pct >= )(-?[\d.]+)( THEN 3)', fr'\g<1>{p["margin_p25"]:.4f}\g<3>')
    sub(r'(WHEN m\.loaded_margin_pct >= )(-?[\d.]+)( THEN 2)', fr'\g<1>{p["margin_p10"]:.4f}\g<3>')

    # Q2: shelf-cost thresholds
    sub(r'(WHEN s\.annual_shelf_space_cost <= )([\d.]+)( THEN 5)', fr'\g<1>{p["shelf_p25"]:.2f}\g<3>')
    sub(r'(WHEN s\.annual_shelf_space_cost <= )([\d.]+)( THEN 4)', fr'\g<1>{p["shelf_p50"]:.2f}\g<3>')
    sub(r'(WHEN s\.annual_shelf_space_cost <= )([\d.]+)( THEN 3)', fr'\g<1>{p["shelf_p75"]:.2f}\g<3>')
    sub(r'(WHEN s\.annual_shelf_space_cost <= )([\d.]+)( THEN 2)', fr'\g<1>{p["shelf_p90"]:.2f}\g<3>')

    # Q2: complexity thresholds — anchor on the NULLIF(pm.msrp,...)) <= X sequence
    sub(r'(NULLIF\(pm\.msrp,\s*0\)\)\s*<=\s*)([\d.]+)(\s+THEN 5)', fr'\g<1>{p["complex_p25"]:.4f}\g<3>')
    sub(r'(NULLIF\(pm\.msrp,\s*0\)\)\s*<=\s*)([\d.]+)(\s+THEN 4)', fr'\g<1>{p["complex_p50"]:.4f}\g<3>')
    sub(r'(NULLIF\(pm\.msrp,\s*0\)\)\s*<=\s*)([\d.]+)(\s+THEN 3)', fr'\g<1>{p["complex_p75"]:.4f}\g<3>')
    sub(r'(NULLIF\(pm\.msrp,\s*0\)\)\s*<=\s*)([\d.]+)(\s+THEN 2)', fr'\g<1>{p["complex_p90"]:.4f}\g<3>')

    # Q2: cannibalization thresholds — the 0.0 check line stays as-is (no threshold)
    sub(r'(GREATEST\(0,\s*-cp\.velocity_delta_pct\)\s*<=\s*)([\d.]+)(\s+THEN 4)', fr'\g<1>{p["cannibal_p50"]:.4f}\g<3>')
    sub(r'(GREATEST\(0,\s*-cp\.velocity_delta_pct\)\s*<=\s*)([\d.]+)(\s+THEN 3)', fr'\g<1>{p["cannibal_p75"]:.4f}\g<3>')
    sub(r'(GREATEST\(0,\s*-cp\.velocity_delta_pct\)\s*<=\s*)([\d.]+)(\s+THEN 2)', fr'\g<1>{p["cannibal_p90"]:.4f}\g<3>')

    # Q3: simplified binary CASE blocks — score >= 3 boundary (not a red flag)
    # velocity/margin use P25; shelf/complexity/cannibalization use P75.
    sub(
        r'CASE WHEN v\.uspw >= [\d.]+ THEN 0 ELSE 1 END',
        f"CASE WHEN v.uspw >= {p['vel_p25']:.4f} THEN 0 ELSE 1 END",
    )
    sub(
        r'CASE WHEN m\.loaded_margin_pct >= -?[\d.]+ THEN 0 ELSE 1 END',
        f"CASE WHEN m.loaded_margin_pct >= {p['margin_p25']:.4f} THEN 0 ELSE 1 END",
    )
    sub(
        r'CASE WHEN s\.annual_shelf_space_cost <= [\d.]+ THEN 0 ELSE 1 END',
        f"CASE WHEN s.annual_shelf_space_cost <= {p['shelf_p75']:.2f} THEN 0 ELSE 1 END",
    )
    sub(
        r'CASE WHEN \(sc\.landed_cost_per_unit/NULLIF\(pm\.msrp,0\)\) <= [\d.]+ THEN 0 ELSE 1 END',
        f"CASE WHEN (sc.landed_cost_per_unit/NULLIF(pm.msrp,0)) <= {p['complex_p75']:.4f} THEN 0 ELSE 1 END",
    )
    sub(
        r'CASE WHEN COALESCE\(GREATEST\(0,-cp\.velocity_delta_pct\),0\) <= [\d.]+ THEN 0 ELSE 1 END',
        f"CASE WHEN COALESCE(GREATEST(0,-cp.velocity_delta_pct),0) <= {p['cannibal_p75']:.4f} THEN 0 ELSE 1 END",
    )

    sql_path.write_text(sql, encoding="utf-8")
    print(f"  SQL thresholds synced in {sql_path.name}")


def render_constants(p: dict) -> str:
    return textwrap.dedent(f"""\
        # Auto-generated by scripts/calibrate.py — do not edit by hand.
        # Source: Cinderhaven Postgres percentile distributions (2023-2026 window).
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
        # 0.0 = no signal, positive = velocity drops in shared stores.
        # HIGH / VERY_HIGH are fixed cutoffs from the pre-zeroing PAIRS distribution
        # (int_cannibalization_pairs), where the metric is defined — NOT percentiles
        # of the shipped per-SKU values (36/50 are zeroed, so those measure the zero
        # mass). See docs/scoring_methodology.md.
        CANNIBAL_P10 = {p['cannibal_p10']:.4f}
        CANNIBAL_P25 = {p['cannibal_p25']:.4f}
        CANNIBAL_P50 = {p['cannibal_p50']:.4f}
        CANNIBAL_HIGH = {p['cannibal_p75']:.4f}       # pairs-distribution p75
        CANNIBAL_VERY_HIGH = {p['cannibal_p90']:.4f}  # pairs-distribution p90
    """)


def main() -> None:
    print("Connecting to Cinderhaven Postgres via proxy...")
    try:
        conn = connect(PLATFORM_ENV)
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

    validate_percentiles(p)

    out_path = Path(__file__).parent.parent / "src" / "scoring" / "constants.py"
    out_path.write_text(render_constants(p), encoding="utf-8")
    print(f"\nThresholds written to {out_path}")

    sql_path = Path(__file__).parent.parent / "sql" / "diagnostic_queries.sql"
    sync_sql_thresholds(p, sql_path)
    print("Calibration complete.")


if __name__ == "__main__":
    main()
