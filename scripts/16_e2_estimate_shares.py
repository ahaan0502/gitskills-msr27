#!/usr/bin/env python3
"""E2 step 6: estimate creation and maintenance shares by required strata."""
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--classifications", type=Path, default=OUT_DIR / "e2_authorship_classifications.parquet")
    ap.add_argument("--language", type=Path, default=OUT_DIR / "e1_language.parquet")
    ap.add_argument("--flags", type=Path, default=OUT_DIR / "skills_flags.parquet")
    ap.add_argument("--out", type=Path, default=OUT_DIR / "e2_step6_summary.csv")
    ap.add_argument("--overall-out", type=Path, default=OUT_DIR / "e2_step6_overall.csv")
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    raw = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    classifications = str(args.classifications).replace("\\", "/")
    language = str(args.language).replace("\\", "/")
    flags = str(args.flags).replace("\\", "/")
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"""
      CREATE OR REPLACE TEMP TABLE base AS
      SELECT c.file_sha,
             c.history_quality,
             c.creation_agent_explicit,
             c.maintenance_agent_explicit,
             c.maintenance_agent_any_event,
             CASE WHEN TRY_CAST(a.first_commit_at AS TIMESTAMP)
                        BETWEEN TIMESTAMP '2025-10-01' AND TIMESTAMP '2026-07-31 23:59:59'
                  THEN strftime(TRY_CAST(a.first_commit_at AS TIMESTAMP), '%Y-%m')
                  ELSE 'other_or_undated' END AS cohort,
             COALESCE(a.location_class, 'unknown') AS location_class,
             COALESCE(l.body_language, 'unknown_or_undetermined') AS language,
             COALESCE(CAST(f.catalog_flag AS VARCHAR), 'false') AS catalog_flag,
             COALESCE(CAST(f.template_flag AS VARCHAR), 'false') AS template_flag,
             COALESCE(CAST(f.bulk_repo_flag AS VARCHAR), 'false') AS bulk_repo_flag
      FROM read_parquet('{classifications}') c
      JOIN read_parquet('{raw}') a USING (file_sha)
      LEFT JOIN read_parquet('{language}') l USING (file_sha)
      LEFT JOIN read_parquet('{flags}') f USING (file_sha)
      WHERE a.dedup_primary = 1
    """)
    dimensions = {
        "overall": "'all'",
        "cohort": "cohort",
        "language": "language",
        "location_class": "location_class",
        "catalog_flag": "catalog_flag",
        "template_flag": "template_flag",
        "bulk_repo_flag": "bulk_repo_flag",
        "history_quality": "COALESCE(history_quality, 'unknown_history')",
    }
    frames: list[pd.DataFrame] = []
    for dimension, expression in dimensions.items():
        frame = con.execute(f"""
          SELECT '{dimension}' AS dimension, {expression} AS stratum,
                 COUNT(*)::BIGINT AS n_total,
                 COUNT(*) FILTER (WHERE history_quality IS NOT NULL)::BIGINT AS n_history,
                 COUNT(*) FILTER (WHERE history_quality IS NULL)::BIGINT AS n_unknown_history,
                 COUNT(*) FILTER (WHERE history_quality IS NOT NULL AND creation_agent_explicit)::BIGINT AS creation_positive,
                 COUNT(*) FILTER (WHERE history_quality IS NOT NULL AND maintenance_agent_explicit)::BIGINT AS maintenance_positive,
                 COUNT(*) FILTER (WHERE history_quality IS NOT NULL AND maintenance_agent_any_event)::BIGINT AS maintenance_any_positive
          FROM base GROUP BY 1, 2 ORDER BY 2
        """).df()
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True)
    for prefix in ["creation", "maintenance", "maintenance_any"]:
        positive = f"{prefix}_positive"
        result[f"{prefix}_share_history"] = result[positive] / result.n_history.replace(0, pd.NA)
        intervals = result.apply(lambda r: wilson(int(r[positive]), int(r.n_history)), axis=1)
        result[f"{prefix}_wilson95_low"] = [x[0] for x in intervals]
        result[f"{prefix}_wilson95_high"] = [x[1] for x in intervals]
        result[f"{prefix}_share_all"] = result[positive] / result.n_total.replace(0, pd.NA)
    result.to_csv(args.out, index=False)
    result[result.dimension == "overall"].to_csv(args.overall_out, index=False)
    print(result[result.dimension == "overall"].to_string(index=False))
    print(f"Wrote {args.out}")
    print(f"Wrote {args.overall_out}")
    con.close()


if __name__ == "__main__":
    main()
