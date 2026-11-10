#!/usr/bin/env python3
"""E1 step 5: aggregate overall language shares with explicit unknowns."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gitskills.config import OUT_DIR  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--language", type=Path, default=OUT_DIR / "e1_language.parquet")
    ap.add_argument("--out", type=Path, default=OUT_DIR / "e1_overall_language_shares.csv")
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    language = str(args.language).replace("\\", "/")
    out = str(args.out).replace("\\", "/")
    con = duckdb.connect()
    con.execute(f"""
        COPY (
            WITH skill_fields AS (
                SELECT 'description' AS unit,
                       COALESCE(description_language, 'unknown_or_undetermined') AS language,
                       file_sha,
                       1::BIGINT AS observation
                FROM read_parquet('{language}')
                UNION ALL
                SELECT 'body_prose' AS unit,
                       COALESCE(body_language, 'unknown_or_undetermined') AS language,
                       file_sha,
                       1::BIGINT AS observation
                FROM read_parquet('{language}')
            ),
            paragraph_fields AS (
                SELECT 'paragraph' AS unit,
                       COALESCE(p.language, 'unknown_or_undetermined') AS language,
                       l.file_sha,
                       1::BIGINT AS observation
                FROM read_parquet('{language}') l,
                     UNNEST(l.paragraph_languages) AS p(language)
            ),
            all_fields AS (
                SELECT * FROM skill_fields
                UNION ALL
                SELECT * FROM paragraph_fields
            ),
            denominators AS (
                SELECT unit, SUM(observation) AS denominator
                FROM all_fields GROUP BY unit
            )
            SELECT a.unit,
                   a.language,
                   SUM(a.observation)::BIGINT AS n_observations,
                   COUNT(DISTINCT a.file_sha)::BIGINT AS n_distinct_skills,
                   d.denominator,
                   ROUND(SUM(a.observation)::DOUBLE / d.denominator, 8) AS share
            FROM all_fields a
            JOIN denominators d USING (unit)
            GROUP BY a.unit, a.language, d.denominator
            ORDER BY a.unit, n_observations DESC
        ) TO '{out}' (FORMAT CSV, HEADER)
    """)
    print(f"Wrote {args.out}")
    print(con.execute(f"SELECT * FROM read_csv_auto('{out}')").df().to_string(index=False))


if __name__ == "__main__":
    main()
