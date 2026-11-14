#!/usr/bin/env python3
"""E3-r01 Step 3: validate structural features and write an anonymized sample."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

from gitskills.config import OUT_DIR
from gitskills.config import RAW_DIR
from gitskills.structure import STRUCTURE_VERSION


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default="E3-r01-primary")
    ap.add_argument("--skills", type=Path, default=OUT_DIR / "skills.parquet")
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--flags", type=Path, default=OUT_DIR / "skills_flags.parquet")
    ap.add_argument("--features", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--sample-size", type=int, default=200)
    args = ap.parse_args()
    features = args.features or OUT_DIR / "runs" / args.run_id / "structural_features.parquet"
    out_dir = args.out_dir or OUT_DIR / "runs" / args.run_id / "step3_structure_validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    f = str(features).replace("\\", "/")
    s = str(args.skills).replace("\\", "/")
    raw = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    flags = str(args.flags).replace("\\", "/")
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{f}')").df()
    schema.to_csv(out_dir / "feature_schema.csv", index=False)
    metrics = con.execute(f"""
      WITH joined AS (
        SELECT s.file_sha, s.body_chars AS expected_body_chars,
               s.body_words AS expected_body_words, s.body_lines AS expected_body_lines,
               s.n_headings AS expected_headings, s.fm_keys AS expected_fm_keys,
               s.parse_error, s.is_empty, s.is_symlink_like,
               e.* EXCLUDE (file_sha)
        FROM read_parquet('{s}') s
        LEFT JOIN read_parquet('{f}') e USING (file_sha)
      ), checks AS (
        SELECT *,
          body_chars = expected_body_chars AS body_chars_match,
          body_words = expected_body_words AS body_words_match,
          body_lines = expected_body_lines AS body_lines_match,
          n_headings = expected_headings AS heading_count_match,
          array_length(heading_levels) = n_headings AS heading_level_length_match,
          array_length(heading_names) = n_headings AS heading_name_length_match,
          frontmatter_key_count = array_length(list_distinct(list_transform(expected_fm_keys, lambda x: lower(trim(x))))) AS frontmatter_key_count_match,
          CASE WHEN is_empty THEN structure_status = 'empty'
               WHEN is_symlink_like THEN structure_status = 'symlink_like'
               WHEN parse_error IS NOT NULL AND parse_error <> '' THEN structure_status = 'parser_error_present'
               ELSE structure_status = 'ok' END AS status_match,
          structure_version = '{STRUCTURE_VERSION}' AS version_match
        FROM joined
      )
      SELECT 'skills_rows' AS metric, COUNT(*)::BIGINT AS value FROM read_parquet('{s}')
      UNION ALL SELECT 'feature_rows', COUNT(*)::BIGINT FROM read_parquet('{f}')
      UNION ALL SELECT 'feature_distinct_file_sha', COUNT(DISTINCT file_sha)::BIGINT FROM read_parquet('{f}')
      UNION ALL SELECT 'missing_feature_rows', COUNT(*) FILTER (WHERE structure_status IS NULL)::BIGINT FROM checks
      UNION ALL SELECT 'body_chars_match', COUNT(*) FILTER (WHERE body_chars_match)::BIGINT FROM checks
      UNION ALL SELECT 'body_words_match', COUNT(*) FILTER (WHERE body_words_match)::BIGINT FROM checks
      UNION ALL SELECT 'body_lines_match', COUNT(*) FILTER (WHERE body_lines_match)::BIGINT FROM checks
      UNION ALL SELECT 'heading_count_match', COUNT(*) FILTER (WHERE heading_count_match)::BIGINT FROM checks
      UNION ALL SELECT 'heading_level_length_match', COUNT(*) FILTER (WHERE heading_level_length_match)::BIGINT FROM checks
      UNION ALL SELECT 'heading_name_length_match', COUNT(*) FILTER (WHERE heading_name_length_match)::BIGINT FROM checks
      UNION ALL SELECT 'frontmatter_key_count_match', COUNT(*) FILTER (WHERE frontmatter_key_count_match)::BIGINT FROM checks
      UNION ALL SELECT 'status_match', COUNT(*) FILTER (WHERE status_match)::BIGINT FROM checks
      UNION ALL SELECT 'version_match', COUNT(*) FILTER (WHERE version_match)::BIGINT FROM checks
    """).df()
    metrics.to_csv(out_dir / "validation_metrics.csv", index=False)
    metadata_metrics = con.execute(f"""
      WITH expected AS (
        SELECT a.file_sha,
               CASE WHEN TRY_CAST(a.first_commit_at AS TIMESTAMP)
                          BETWEEN TIMESTAMP '2025-10-01' AND TIMESTAMP '2026-07-31 23:59:59'
                    THEN strftime(TRY_CAST(a.first_commit_at AS TIMESTAMP), '%Y-%m')
                    ELSE 'other_or_undated' END AS expected_cohort,
               COALESCE(a.location_class, 'unknown') AS expected_location,
               g.catalog_flag AS expected_catalog_flag,
               g.template_flag AS expected_template_flag,
               g.bulk_repo_flag AS expected_bulk_repo_flag,
               g.repo_rank AS expected_repo_rank
        FROM read_parquet('{raw}') a
        JOIN read_parquet('{flags}') g USING (file_sha)
        WHERE a.dedup_primary = 1
      ), joined AS (
        SELECT e.*, f.cohort, f.location_class, f.catalog_flag, f.template_flag,
               f.bulk_repo_flag, f.repo_rank
        FROM expected e JOIN read_parquet('{f}') f USING (file_sha)
      )
      SELECT 'cohort_match' AS metric, COUNT(*) FILTER (WHERE cohort = expected_cohort)::BIGINT AS value FROM joined
      UNION ALL SELECT 'location_class_match', COUNT(*) FILTER (WHERE location_class = expected_location)::BIGINT FROM joined
      UNION ALL SELECT 'catalog_flag_match', COUNT(*) FILTER (WHERE catalog_flag = expected_catalog_flag)::BIGINT FROM joined
      UNION ALL SELECT 'template_flag_match', COUNT(*) FILTER (WHERE template_flag = expected_template_flag)::BIGINT FROM joined
      UNION ALL SELECT 'bulk_repo_flag_match', COUNT(*) FILTER (WHERE bulk_repo_flag = expected_bulk_repo_flag)::BIGINT FROM joined
      UNION ALL SELECT 'repo_rank_match', COUNT(*) FILTER (WHERE repo_rank = expected_repo_rank)::BIGINT FROM joined
      UNION ALL SELECT 'metadata_rows', COUNT(*)::BIGINT FROM joined
    """).df()
    metrics = pd.concat([metrics, metadata_metrics], ignore_index=True)
    metrics.to_csv(out_dir / "validation_metrics.csv", index=False)
    con.execute(f"""
      COPY (
        SELECT file_sha, structure_version, structure_status, body_chars, body_words, body_lines,
               n_paragraphs, n_headings, heading_levels, heading_names, max_heading_depth,
               n_bullet_lists, n_ordered_lists, n_blockquotes, n_tables, n_code_blocks,
               n_inline_code, n_thematic_breaks, frontmatter_key_count, has_name_key,
               has_description_key, template_signature
        FROM read_parquet('{f}')
        QUALIFY row_number() OVER (ORDER BY hash(file_sha || ':e3-step3')) <= {int(args.sample_size)}
      ) TO '{str(out_dir / 'anonymized_sample.csv').replace(chr(92), '/')}' (FORMAT CSV, HEADER)
    """)
    status = con.execute(f"SELECT structure_status, COUNT(*) AS n FROM read_parquet('{f}') GROUP BY 1 ORDER BY 1").df()
    status.to_csv(out_dir / "status_counts.csv", index=False)
    summary = {
        "run_id": args.run_id,
        "structure_version": STRUCTURE_VERSION,
        "sample_size": args.sample_size,
        "metrics": {str(r.metric): int(r.value) for r in metrics.itertuples()},
        "status_counts": {str(r.structure_status): int(r.n) for r in status.itertuples()},
        "raw_text_written": False,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(metrics.to_string(index=False))
    print(status.to_string(index=False))
    print(f"Wrote {out_dir}")
    con.close()


if __name__ == "__main__":
    main()
