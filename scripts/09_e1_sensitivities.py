#!/usr/bin/env python3
"""E1 step 8: copy-inclusive and E0-flag sensitivity summaries."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gitskills.config import OUT_DIR, RAW_DIR  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--language", type=Path, default=OUT_DIR / "e1_language.parquet")
    ap.add_argument("--flags", type=Path, default=OUT_DIR / "skills_flags.parquet")
    ap.add_argument("--language-out", type=Path, default=OUT_DIR / "e1_sensitivity_language.csv")
    ap.add_argument("--agreement-out", type=Path, default=OUT_DIR / "e1_sensitivity_agreement.csv")
    args = ap.parse_args()
    args.language_out.parent.mkdir(parents=True, exist_ok=True)
    raw = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    language = str(args.language).replace("\\", "/")
    flags = str(args.flags).replace("\\", "/")
    lang_out = str(args.language_out).replace("\\", "/")
    agree_out = str(args.agreement_out).replace("\\", "/")
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW skill_views AS
        SELECT 'distinct_content' AS view, l.file_sha, l.description_language,
               l.body_language, l.description_status, l.body_status, 1::BIGINT AS weight
        FROM read_parquet('{language}') l
        UNION ALL
        SELECT 'copy_inclusive', l.file_sha, l.description_language, l.body_language,
               l.description_status, l.body_status, COUNT(*)::BIGINT AS weight
        FROM read_parquet('{language}') l JOIN read_parquet('{raw}') a USING (file_sha)
        GROUP BY ALL
        UNION ALL
        SELECT 'catalog_true', file_sha, description_language, body_language,
               description_status, body_status, 1::BIGINT
        FROM read_parquet('{language}') l JOIN read_parquet('{flags}') f USING (file_sha)
        WHERE catalog_flag
        UNION ALL
        SELECT 'catalog_false', file_sha, description_language, body_language,
               description_status, body_status, 1::BIGINT
        FROM read_parquet('{language}') l JOIN read_parquet('{flags}') f USING (file_sha)
        WHERE NOT catalog_flag
        UNION ALL
        SELECT 'template_true', file_sha, description_language, body_language,
               description_status, body_status, 1::BIGINT
        FROM read_parquet('{language}') l JOIN read_parquet('{flags}') f USING (file_sha)
        WHERE template_flag
        UNION ALL
        SELECT 'template_false', file_sha, description_language, body_language,
               description_status, body_status, 1::BIGINT
        FROM read_parquet('{language}') l JOIN read_parquet('{flags}') f USING (file_sha)
        WHERE NOT template_flag
        UNION ALL
        SELECT 'bulk_repo_true', file_sha, description_language, body_language,
               description_status, body_status, 1::BIGINT
        FROM read_parquet('{language}') l JOIN read_parquet('{flags}') f USING (file_sha)
        WHERE bulk_repo_flag
        UNION ALL
        SELECT 'bulk_repo_false', file_sha, description_language, body_language,
               description_status, body_status, 1::BIGINT
        FROM read_parquet('{language}') l JOIN read_parquet('{flags}') f USING (file_sha)
        WHERE NOT bulk_repo_flag
    """)
    con.execute(f"""
        COPY (
            WITH fields AS (
                SELECT view, 'description' AS unit,
                       COALESCE(description_language, 'unknown_or_undetermined') AS language,
                       file_sha, weight AS observation
                FROM skill_views
                UNION ALL
                SELECT view, 'body_prose',
                       COALESCE(body_language, 'unknown_or_undetermined'), file_sha, weight
                FROM skill_views
            ), totals AS (
                SELECT view, unit, SUM(observation) AS denominator
                FROM fields GROUP BY view, unit
            )
            SELECT f.view, f.unit, f.language,
                   SUM(f.observation)::BIGINT AS n_observations,
                   COUNT(DISTINCT f.file_sha)::BIGINT AS n_distinct_skills,
                   t.denominator,
                   ROUND(SUM(f.observation)::DOUBLE / t.denominator, 8) AS share
            FROM fields f JOIN totals t USING (view, unit)
            GROUP BY f.view, f.unit, f.language, t.denominator
            ORDER BY f.view, f.unit, n_observations DESC
        ) TO '{lang_out}' (FORMAT CSV, HEADER)
    """)
    con.execute(f"""
        COPY (
            SELECT view,
                   COUNT(*)::BIGINT AS n_rows,
                   SUM(weight)::BIGINT AS denominator,
                   SUM(weight) FILTER (WHERE description_status = 'detected' AND body_status = 'detected')::BIGINT AS both_confident,
                   SUM(weight) FILTER (WHERE description_status = 'detected' AND body_status = 'detected' AND description_language = body_language)::BIGINT AS agree_both_confident,
                   ROUND(
                       SUM(weight) FILTER (WHERE description_status = 'detected' AND body_status = 'detected' AND description_language = body_language)::DOUBLE
                       / NULLIF(SUM(weight) FILTER (WHERE description_status = 'detected' AND body_status = 'detected'), 0), 8
                   ) AS agreement_rate
            FROM skill_views GROUP BY view ORDER BY view
        ) TO '{agree_out}' (FORMAT CSV, HEADER)
    """)
    print(f"Wrote {args.language_out}")
    print(con.execute(f"SELECT * FROM read_csv_auto('{lang_out}') WHERE language IN ('en', 'unknown_or_undetermined') ORDER BY view, unit, language").df().to_string(index=False))
    print(f"Wrote {args.agreement_out}")
    print(con.execute(f"SELECT * FROM read_csv_auto('{agree_out}')").df().to_string(index=False))


if __name__ == "__main__":
    main()
