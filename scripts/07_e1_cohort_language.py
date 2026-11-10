#!/usr/bin/env python3
"""E1 step 6: aggregate language shares by the E0-valid monthly cohort."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gitskills.config import COLLECTION_END, FORMAT_START, OUT_DIR, RAW_DIR  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--language", type=Path, default=OUT_DIR / "e1_language.parquet")
    ap.add_argument("--out", type=Path, default=OUT_DIR / "e1_cohort_language_shares.csv")
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    raw = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    language = str(args.language).replace("\\", "/")
    out = str(args.out).replace("\\", "/")
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"""
        COPY (
            WITH cohort_skills AS (
                SELECT file_sha,
                       strftime(TRY_CAST(first_commit_at AS TIMESTAMP), '%Y-%m') AS cohort
                FROM read_parquet('{raw}')
                WHERE dedup_primary = 1
                  AND TRY_CAST(first_commit_at AS TIMESTAMP)
                      BETWEEN TIMESTAMP '{FORMAT_START}' AND TIMESTAMP '{COLLECTION_END} 23:59:59'
            ),
            skill_fields AS (
                SELECT 'description' AS unit, l.description_language AS language,
                       l.file_sha, c.cohort, 1::BIGINT AS observation
                FROM read_parquet('{language}') l JOIN cohort_skills c USING (file_sha)
                UNION ALL
                SELECT 'body_prose', l.body_language, l.file_sha, c.cohort, 1::BIGINT
                FROM read_parquet('{language}') l JOIN cohort_skills c USING (file_sha)
            ),
            paragraph_fields AS (
                SELECT 'paragraph' AS unit, p.language, l.file_sha, c.cohort, 1::BIGINT AS observation
                FROM read_parquet('{language}') l
                JOIN cohort_skills c USING (file_sha),
                     UNNEST(l.paragraph_languages) AS p(language)
            ),
            all_fields AS (
                SELECT unit, COALESCE(language, 'unknown_or_undetermined') AS language,
                       file_sha, cohort, observation FROM skill_fields
                UNION ALL
                SELECT unit, COALESCE(language, 'unknown_or_undetermined'),
                       file_sha, cohort, observation FROM paragraph_fields
            ),
            grouped AS (
                SELECT unit, cohort, language,
                       SUM(observation)::BIGINT AS n_observations,
                       COUNT(DISTINCT file_sha)::BIGINT AS n_distinct_skills
                FROM all_fields
                GROUP BY unit, cohort, language
            ),
            with_totals AS (
                SELECT *,
                       SUM(n_observations) OVER (PARTITION BY unit, cohort) AS denominator,
                       SUM(CASE WHEN language = 'unknown_or_undetermined'
                                THEN n_observations ELSE 0 END)
                           OVER (PARTITION BY unit, cohort) AS unknown_observations
                FROM grouped
            )
            SELECT unit, cohort, language, n_observations, n_distinct_skills,
                   denominator, unknown_observations,
                   ROUND(n_observations::DOUBLE / denominator, 8) AS share,
                   ROUND(unknown_observations::DOUBLE / denominator, 8) AS unknown_share
            FROM with_totals
            ORDER BY unit, cohort, n_observations DESC
        ) TO '{out}' (FORMAT CSV, HEADER)
    """)
    print(f"Wrote {args.out}")
    print(con.execute(f"""
        SELECT unit, COUNT(*) AS rows, MIN(cohort) AS first_cohort,
               MAX(cohort) AS last_cohort, MAX(denominator) AS max_denominator
        FROM read_csv_auto('{out}') GROUP BY unit ORDER BY unit
    """).df().to_string(index=False))


if __name__ == "__main__":
    main()
