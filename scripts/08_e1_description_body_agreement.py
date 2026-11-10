#!/usr/bin/env python3
"""E1 step 7: compare description and body language labels."""
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
    ap.add_argument("--out", type=Path, default=OUT_DIR / "e1_description_body_agreement.csv")
    ap.add_argument("--matrix-out", type=Path, default=OUT_DIR / "e1_description_body_matrix.csv")
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    language = str(args.language).replace("\\", "/")
    out = str(args.out).replace("\\", "/")
    matrix_out = str(args.matrix_out).replace("\\", "/")
    con = duckdb.connect()
    base = f"read_parquet('{language}')"
    con.execute(f"""
        COPY (
            WITH b AS (
                SELECT *,
                       description_status = 'detected' AS desc_confident,
                       body_status = 'detected' AS body_confident,
                       description_status IN ('detected', 'short_text') AS desc_labeled,
                       body_status IN ('detected', 'short_text') AS body_labeled
                FROM {base}
            ),
            paragraph_languages AS (
                SELECT file_sha, COUNT(DISTINCT p.language) FILTER (WHERE p.language IS NOT NULL) AS n_languages
                FROM {base} l, UNNEST(l.paragraph_languages) AS p(language)
                GROUP BY file_sha
            ),
            values AS (
                SELECT 'total_skills' AS metric, COUNT(*)::BIGINT AS n, COUNT(*)::BIGINT AS denominator FROM b
                UNION ALL SELECT 'both_confident', COUNT(*) FILTER (WHERE desc_confident AND body_confident), COUNT(*) FROM b
                UNION ALL SELECT 'agree_both_confident', COUNT(*) FILTER (WHERE desc_confident AND body_confident AND description_language = body_language), COUNT(*) FILTER (WHERE desc_confident AND body_confident) FROM b
                UNION ALL SELECT 'both_labeled_including_short', COUNT(*) FILTER (WHERE desc_labeled AND body_labeled), COUNT(*) FROM b
                UNION ALL SELECT 'agree_including_short', COUNT(*) FILTER (WHERE desc_labeled AND body_labeled AND description_language = body_language), COUNT(*) FILTER (WHERE desc_labeled AND body_labeled) FROM b
                UNION ALL SELECT 'description_only_labeled', COUNT(*) FILTER (WHERE desc_labeled AND NOT body_labeled), COUNT(*) FROM b
                UNION ALL SELECT 'body_only_labeled', COUNT(*) FILTER (WHERE body_labeled AND NOT desc_labeled), COUNT(*) FROM b
                UNION ALL SELECT 'neither_labeled', COUNT(*) FILTER (WHERE NOT desc_labeled AND NOT body_labeled), COUNT(*) FROM b
                UNION ALL SELECT 'description_unknown_or_undetermined', COUNT(*) FILTER (WHERE description_language IS NULL), COUNT(*) FROM b
                UNION ALL SELECT 'body_unknown_or_undetermined', COUNT(*) FILTER (WHERE body_language IS NULL), COUNT(*) FROM b
                UNION ALL SELECT 'paragraph_mixed_language', COUNT(*) FILTER (WHERE n_languages > 1), COUNT(*) FROM paragraph_languages
            )
            SELECT metric, n, denominator,
                   CASE WHEN denominator = 0 THEN NULL ELSE ROUND(n::DOUBLE / denominator, 8) END AS rate
            FROM values ORDER BY metric
        ) TO '{out}' (FORMAT CSV, HEADER)
    """)
    con.execute(f"""
        COPY (
            SELECT COALESCE(description_language, 'unknown_or_undetermined') AS description_language,
                   COALESCE(body_language, 'unknown_or_undetermined') AS body_language,
                   COUNT(*)::BIGINT AS n_skills
            FROM {base}
            WHERE description_status = 'detected' AND body_status = 'detected'
            GROUP BY 1, 2 ORDER BY n_skills DESC
        ) TO '{matrix_out}' (FORMAT CSV, HEADER)
    """)
    print(f"Wrote {args.out}")
    print(con.execute(f"SELECT * FROM read_csv_auto('{out}')").df().to_string(index=False))
    print(f"Wrote {args.matrix_out}")


if __name__ == "__main__":
    main()
