#!/usr/bin/env python3
"""E3-r01 Step 1: inventory and freeze E0-derived structural-analysis inputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

from gitskills.config import OUT_DIR, RAW_DIR


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default="E3-r01-primary")
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--skills", type=Path, default=OUT_DIR / "skills.parquet")
    ap.add_argument("--flags", type=Path, default=OUT_DIR / "skills_flags.parquet")
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()
    out_dir = args.out_dir or OUT_DIR / "runs" / args.run_id / "step1_input_inventory"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    skills = str(args.skills).replace("\\", "/")
    flags = str(args.flags).replace("\\", "/")
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")

    skill_schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{skills}')").df()
    flag_schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{flags}')").df()
    artifact_schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{raw}')").df()
    schema = {
        "run_id": args.run_id,
        "skills_fields": skill_schema.column_name.tolist(),
        "flags_fields": flag_schema.column_name.tolist(),
        "artifact_fields": artifact_schema.column_name.tolist(),
    }
    (out_dir / "schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")

    metrics = con.execute(f"""
      SELECT 'skills_rows' AS metric, COUNT(*)::BIGINT AS value FROM read_parquet('{skills}')
      UNION ALL SELECT 'skills_distinct_file_sha', COUNT(DISTINCT file_sha)::BIGINT FROM read_parquet('{skills}')
      UNION ALL SELECT 'skills_spec_valid', COUNT(*) FILTER (WHERE spec_valid)::BIGINT FROM read_parquet('{skills}')
      UNION ALL SELECT 'skills_frontmatter_valid', COUNT(*) FILTER (WHERE frontmatter_valid)::BIGINT FROM read_parquet('{skills}')
      UNION ALL SELECT 'skills_fm_recovered', COUNT(*) FILTER (WHERE fm_recovered)::BIGINT FROM read_parquet('{skills}')
      UNION ALL SELECT 'skills_parse_error', COUNT(*) FILTER (WHERE parse_error IS NOT NULL AND parse_error <> '')::BIGINT FROM read_parquet('{skills}')
      UNION ALL SELECT 'artifact_representatives', COUNT(*) FILTER (WHERE dedup_primary = 1)::BIGINT FROM read_parquet('{raw}')
      UNION ALL SELECT 'artifact_occurrences', COUNT(*)::BIGINT FROM read_parquet('{raw}')
      UNION ALL SELECT 'dated_representatives_e0_window', COUNT(*) FILTER (WHERE dedup_primary = 1 AND TRY_CAST(first_commit_at AS TIMESTAMP) BETWEEN TIMESTAMP '2025-10-01' AND TIMESTAMP '2026-07-31 23:59:59')::BIGINT FROM read_parquet('{raw}')
      UNION ALL SELECT 'flags_rows', COUNT(*)::BIGINT FROM read_parquet('{flags}')
      UNION ALL SELECT 'flags_distinct_file_sha', COUNT(DISTINCT file_sha)::BIGINT FROM read_parquet('{flags}')
      UNION ALL SELECT 'flags_repo_rank_null', COUNT(*) FILTER (WHERE repo_rank IS NULL)::BIGINT FROM read_parquet('{flags}')
      UNION ALL SELECT 'flags_repo_rank_min', MIN(repo_rank)::BIGINT FROM read_parquet('{flags}')
      UNION ALL SELECT 'flags_repo_rank_max', MAX(repo_rank)::BIGINT FROM read_parquet('{flags}')
      UNION ALL SELECT 'catalog_flag_true', COUNT(*) FILTER (WHERE catalog_flag)::BIGINT FROM read_parquet('{flags}')
      UNION ALL SELECT 'template_flag_true', COUNT(*) FILTER (WHERE template_flag)::BIGINT FROM read_parquet('{flags}')
      UNION ALL SELECT 'bulk_repo_flag_true', COUNT(*) FILTER (WHERE bulk_repo_flag)::BIGINT FROM read_parquet('{flags}')
    """).df()
    metrics.to_csv(out_dir / "metrics.csv", index=False)

    con.execute(f"""
      COPY (
        SELECT CASE WHEN TRY_CAST(first_commit_at AS TIMESTAMP)
                          BETWEEN TIMESTAMP '2025-10-01' AND TIMESTAMP '2026-07-31 23:59:59'
                    THEN strftime(TRY_CAST(first_commit_at AS TIMESTAMP), '%Y-%m')
                    ELSE 'other_or_undated' END AS cohort,
               COUNT(*)::BIGINT AS representatives,
               COUNT(*) FILTER (WHERE first_commit_at IS NOT NULL)::BIGINT AS with_first_commit_at
        FROM read_parquet('{raw}')
        WHERE dedup_primary = 1
        GROUP BY 1 ORDER BY 1
      ) TO '{str(out_dir / 'cohort_counts.csv').replace(chr(92), '/')}' (FORMAT CSV, HEADER)
    """)

    summary = {row.metric: int(row.value) if pd.notna(row.value) else None for row in metrics.itertuples()}
    summary["e0_window_share_of_representatives"] = summary["dated_representatives_e0_window"] / summary["artifact_representatives"]
    summary["run_id"] = args.run_id
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote {out_dir}")
    con.close()


if __name__ == "__main__":
    main()
