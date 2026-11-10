#!/usr/bin/env python3
"""E2 step 7: robustness and repository-concentration sensitivities."""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import duckdb
import pandas as pd

from gitskills.config import OUT_DIR, RAW_DIR


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if total == 0:
        return None, None
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return max(0.0, center - half), min(1.0, center + half)


def summarize(con: duckdb.DuckDBPyConnection, name: str, relation: str) -> dict[str, object]:
    row = con.execute(f"""
      SELECT '{name}' AS sensitivity, COUNT(*)::BIGINT AS n_total,
             COUNT(*) FILTER (WHERE history_quality IS NOT NULL)::BIGINT AS n_history,
             COUNT(*) FILTER (WHERE history_quality IS NULL)::BIGINT AS n_unknown_history,
             COUNT(*) FILTER (WHERE history_quality IS NOT NULL AND creation_agent_explicit)::BIGINT AS creation_positive,
             COUNT(*) FILTER (WHERE history_quality IS NOT NULL AND maintenance_agent_explicit)::BIGINT AS maintenance_positive,
             COUNT(*) FILTER (WHERE history_quality IS NOT NULL AND maintenance_agent_any_event)::BIGINT AS maintenance_any_positive
      FROM {relation}
    """).fetchone()
    columns = ["sensitivity", "n_total", "n_history", "n_unknown_history", "creation_positive", "maintenance_positive", "maintenance_any_positive"]
    result = dict(zip(columns, row))
    for prefix in ["creation", "maintenance", "maintenance_any"]:
        positive = int(result[f"{prefix}_positive"])
        history = int(result["n_history"])
        result[f"{prefix}_share_history"] = positive / history if history else None
        result[f"{prefix}_share_all"] = positive / int(result["n_total"]) if result["n_total"] else None
        low, high = wilson(positive, history)
        result[f"{prefix}_wilson95_low"] = low
        result[f"{prefix}_wilson95_high"] = high
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--classifications", type=Path, default=OUT_DIR / "e2_authorship_classifications.parquet")
    ap.add_argument("--flags", type=Path, default=OUT_DIR / "skills_flags.parquet")
    ap.add_argument("--out", type=Path, default=OUT_DIR / "e2_step7_robustness.csv")
    ap.add_argument("--repo-cap", type=int, default=50)
    args = ap.parse_args()
    if args.repo_cap < 1:
        raise SystemExit("repo cap must be positive")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    raw = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    classifications = str(args.classifications).replace("\\", "/")
    flags = str(args.flags).replace("\\", "/")
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"""
      CREATE OR REPLACE TEMP TABLE primary_base AS
      SELECT c.*, f.repo_full_name, f.repo_rank, f.catalog_flag, f.template_flag, f.bulk_repo_flag,
             CASE WHEN TRY_CAST(a.first_commit_at AS TIMESTAMP)
                        BETWEEN TIMESTAMP '2025-10-01' AND TIMESTAMP '2026-07-31 23:59:59'
                  THEN TRUE ELSE FALSE END AS dated_history
      FROM read_parquet('{classifications}') c
      JOIN read_parquet('{flags}') f USING (file_sha)
      JOIN read_parquet('{raw}') a USING (file_sha)
      WHERE a.dedup_primary = 1
    """)
    con.execute(f"""
      CREATE OR REPLACE TEMP TABLE occurrences AS
      SELECT c.*, a.repo_full_name AS occurrence_repo
      FROM read_parquet('{classifications}') c
      JOIN read_parquet('{raw}') a USING (file_sha)
    """)
    relations: list[tuple[str, str]] = [
        ("distinct_explicit_all", "primary_base"),
        ("distinct_expanded_currently_same_as_explicit", "primary_base"),
        ("history_available_only", "(SELECT * FROM primary_base WHERE history_quality IS NOT NULL)"),
        ("dated_history_only", "(SELECT * FROM primary_base WHERE dated_history AND history_quality IS NOT NULL)"),
        ("exclude_catalog", "(SELECT * FROM primary_base WHERE NOT catalog_flag)"),
        ("exclude_template", "(SELECT * FROM primary_base WHERE NOT template_flag)"),
        ("exclude_bulk_repo", "(SELECT * FROM primary_base WHERE NOT bulk_repo_flag)"),
        ("exclude_catalog_template_bulk", "(SELECT * FROM primary_base WHERE NOT catalog_flag AND NOT template_flag AND NOT bulk_repo_flag)"),
        (f"repo_cap_{args.repo_cap}", f"(SELECT * FROM primary_base WHERE repo_rank <= {args.repo_cap})"),
        ("copy_inclusive_occurrences", "occurrences"),
    ]
    rows = [summarize(con, name, relation) for name, relation in relations]
    result = pd.DataFrame(rows)
    result.to_csv(args.out, index=False)
    print(result[["sensitivity", "n_total", "n_history", "n_unknown_history", "creation_positive", "maintenance_positive", "maintenance_any_positive", "creation_share_history", "maintenance_share_history", "maintenance_any_share_history"]].to_string(index=False))
    print(f"Wrote {args.out}")
    con.close()


if __name__ == "__main__":
    main()
