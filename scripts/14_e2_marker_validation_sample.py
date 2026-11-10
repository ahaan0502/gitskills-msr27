#!/usr/bin/env python3
"""E2 step 5: create an anonymized, stratified marker-validation review frame."""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

from gitskills.config import OUT_DIR, RAW_DIR


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--skills", type=Path, default=OUT_DIR / "skills.parquet")
    ap.add_argument("--flags", type=Path, default=OUT_DIR / "skills_flags.parquet")
    ap.add_argument("--evidence", type=Path, default=OUT_DIR / "e2_authorship_evidence.parquet")
    ap.add_argument("--language", type=Path, default=OUT_DIR / "e1_language.parquet")
    ap.add_argument("--out", type=Path, default=OUT_DIR / "e2_marker_validation_sample.csv")
    ap.add_argument("--per-cell", type=int, default=1)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    raw = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    skills = str(args.skills).replace("\\", "/")
    flags = str(args.flags).replace("\\", "/")
    evidence = str(args.evidence).replace("\\", "/")
    language = str(args.language).replace("\\", "/")
    out = str(args.out).replace("\\", "/")
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"""
      COPY (
        WITH cohort AS (
          SELECT file_sha,
                 CASE WHEN TRY_CAST(first_commit_at AS TIMESTAMP)
                                BETWEEN TIMESTAMP '2025-10-01' AND TIMESTAMP '2026-07-31 23:59:59'
                      THEN strftime(TRY_CAST(first_commit_at AS TIMESTAMP), '%Y-%m')
                      ELSE 'other_or_undated' END AS cohort,
                 location_class
          FROM read_parquet('{raw}') WHERE dedup_primary = 1
        ), base AS (
          SELECT e.file_sha, e.event_position, e.history_quality,
                 e.author_type_category, e.identity_marker, e.identity_specificity,
                 e.identity_reasons, e.message_marker, e.message_specificity,
                 e.message_reasons, e.content_marker, e.content_specificity,
                 e.content_reasons, c.cohort, c.location_class,
                 COALESCE(l.body_language, 'unknown_or_undetermined') AS language,
                 CASE WHEN length(COALESCE(s.body_prose, '')) < 80 THEN 'short'
                      WHEN length(COALESCE(s.body_prose, '')) < 400 THEN 'medium'
                      ELSE 'long' END AS text_length_bucket,
                 f.catalog_flag, f.template_flag, f.bulk_repo_flag
          FROM read_parquet('{evidence}') e
          JOIN read_parquet('{skills}') s USING (file_sha)
          LEFT JOIN read_parquet('{flags}') f USING (file_sha)
          LEFT JOIN read_parquet('{language}') l USING (file_sha)
          JOIN cohort c USING (file_sha)
        ), marked AS (
          SELECT *,
            CASE WHEN author_type_category = 'automated'
                      OR identity_specificity = 'high'
                      OR message_specificity = 'high'
                      OR content_specificity = 'high' THEN 'marker_positive'
                 ELSE 'marker_negative' END AS marker_status
          FROM base
          WHERE language IN ('en', 'zh', 'ja', 'de', 'unknown_or_undetermined')
        ), ranked AS (
          SELECT *, row_number() OVER (
            PARTITION BY event_position, cohort, language, text_length_bucket, marker_status
            ORDER BY hash(file_sha || event_position || history_quality)
          ) AS rn
          FROM marked
        )
        SELECT file_sha, event_position, history_quality, cohort, location_class, language,
               text_length_bucket, catalog_flag, template_flag, bulk_repo_flag,
               author_type_category, identity_marker, identity_specificity, identity_reasons,
               message_marker, message_specificity, message_reasons,
               content_marker, content_specificity, content_reasons, marker_status
        FROM ranked WHERE rn <= {int(args.per_cell)}
      ) TO '{out}' (FORMAT CSV, HEADER)
    """)
    review = pd.read_csv(args.out, dtype=str).fillna("")
    review["hand_label"] = ""
    review["label_notes"] = ""
    review.to_csv(args.out, index=False)
    summary = con.execute(f"SELECT COUNT(*) AS rows, COUNT(DISTINCT file_sha) AS skills FROM read_csv_auto('{out}')").df()
    print(summary.to_string(index=False))
    print(con.execute(f"SELECT marker_status, COUNT(*) AS n FROM read_csv_auto('{out}') GROUP BY 1 ORDER BY 1").df().to_string(index=False))
    print(f"Wrote {args.out}")
    con.close()


if __name__ == "__main__":
    main()
