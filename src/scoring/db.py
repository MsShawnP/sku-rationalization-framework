"""Shared Postgres connection helpers for Cinderhaven scripts.

Both run_scoring.py and scripts/calibrate.py use these. Edit here;
both callers pick up the change automatically.

Requires:
  - flyctl proxy running: `flyctl proxy 5432:5432 -a cinderhaven-db`
  - POSTGRES_PASSWORD env var set (or .env loaded via load_env())
"""
from __future__ import annotations

import os
from pathlib import Path

import psycopg2


def load_env(path: Path) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ (no-op if missing)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def connect(env_path: Path) -> psycopg2.extensions.connection:
    """Load env from path and return a psycopg2 connection to Cinderhaven.

    Raises SystemExit with a friendly message if POSTGRES_PASSWORD is unset.
    Raises psycopg2.OperationalError if the connection itself fails (caller
    should catch and re-raise with context, e.g. 'Is flyctl proxy running?').
    """
    load_env(env_path)
    password = os.environ.get("POSTGRES_PASSWORD")
    if not password:
        raise SystemExit(
            "POSTGRES_PASSWORD is not set. "
            "Set it in your environment or place it in the .env file at:\n"
            f"  {env_path}"
        )
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="cinderhaven",
        user="postgres",
        password=password,
    )
