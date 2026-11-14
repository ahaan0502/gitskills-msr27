#!/usr/bin/env python3
"""E3-r01 Step 6: structural robustness to reuse and repository signals.

All outputs are aggregate tables. No repository names, author fields, or raw
skill text are written.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import duckdb
import pandas as pd

from gitskills.config import OUT_DIR, RAW_DIR
from gitskills.structure import STRUCTURE_VERSION


COHORTS = [
    "2025-10", "2025-11", "2025-12", "2026-01", "2026-02",
    "2026-03", "2026-04", "2026-05", "2026-06", "2026-07",
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default="E3-r01-primary")
    ap.add_argument("--features", type=Path, default=None)
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--repo-cap", type=int, default=50)
    args = ap.parse_args()
    if args.repo_cap < 1:
        raise SystemExit("--repo-cap must be positive")

    features = args.features or OUT_DIR / "runs" / args.run_id / "structural_features.parquet"
    out_dir = args.out_dir or OUT_DIR / "runs" / args.run_id / "step6_robustness"
    out_dir.mkdir(parents=True, exist_ok=True)
    feature_path = str(features).replace("\\", "/")
    artifact_path = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    cohort_sql = "(" + ",".join("'" + c + "'" for c in COHORTS) + ")"

    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"""
      CREATE OR REPLACE TEMP TABLE reps AS
      SELECT * FROM read_parquet('{feature_path}')
    """)
    con.execute(f"""
      CREATE OR REPLACE TEMP TABLE occurrences AS
      SELECT a.file_sha, r.cohort, r.location_class, r.catalog_flag,
             r.template_flag, r.bulk_repo_flag, r.repo_rank,
             r.body_chars, r.body_words, r.n_headings, r.n_tables,
             r.n_code_blocks, r.n_inline_code, r.template_signature
      FROM read_parquet('{artifact_path}') a
      JOIN reps r USING (file_sha)
    """)

    # The primary and exclusion populations remain distinct representatives.
    populations = [
        ("distinct_primary", "reps"),
        ("distinct_exclude_catalog", "(SELECT * FROM reps WHERE NOT catalog_flag)"),
        ("distinct_exclude_template", "(SELECT * FROM reps WHERE NOT template_flag)"),
        ("distinct_exclude_bulk", "(SELECT * FROM reps WHERE NOT bulk_repo_flag)"),
        (
            "distinct_exclude_catalog_template_bulk",
            "(SELECT * FROM reps WHERE NOT catalog_flag AND NOT template_flag AND NOT bulk_repo_flag)",
        ),
        (f"distinct_repo_cap_{args.repo_cap}", f"(SELECT * FROM reps WHERE repo_rank <= {args.repo_cap})"),
        ("copy_inclusive_occurrences", "occurrences"),
    ]

    def summary_rows(name: str, relation: str, by_cohort: bool = False) -> pd.DataFrame:
        grouping = "cohort, " if by_cohort else ""
        where = f"WHERE cohort IN {cohort_sql}" if by_cohort else ""
        template_where = (where + " AND " if where else "WHERE ") + "template_signature IS NOT NULL"
        rows = con.execute(f"""
          SELECT {grouping}
                 '{name}' AS sensitivity,
                 COUNT(*)::BIGINT AS n_units,
                 COUNT(DISTINCT file_sha)::BIGINT AS n_distinct_contents,
                 MEDIAN(body_chars) AS body_chars_median,
                 MEDIAN(body_words) AS body_words_median,
                 MEDIAN(n_headings) AS headings_median,
                 AVG((n_headings > 0)::INT)::DOUBLE AS has_heading_share,
                 AVG((n_tables > 0)::INT)::DOUBLE AS has_table_share,
                 AVG((n_code_blocks > 0)::INT)::DOUBLE AS has_code_block_share,
                 AVG((n_inline_code > 0)::INT)::DOUBLE AS has_inline_code_share,
                 COUNT(DISTINCT template_signature)::BIGINT AS n_unique_templates
          FROM {relation}
          {where}
          GROUP BY {"cohort, " if by_cohort else ""} 1
          ORDER BY {"cohort, " if by_cohort else ""} 1
        """).df()

        entropy_group = "1, 2" if by_cohort else "1"
        entropy_order = "1, " if by_cohort else ""
        entropy = con.execute(f"""
          SELECT {grouping} template_signature, COUNT(*)::BIGINT AS n
          FROM {relation}
          {template_where}
          GROUP BY {entropy_group}
          ORDER BY {entropy_order}n DESC
        """).df()
        entropy_rows: list[dict[str, object]] = []
        group_cols = ["cohort"] if by_cohort else []
        groups = entropy.groupby(group_cols, sort=True) if by_cohort else [(None, entropy)]
        for key, group in groups:
            counts = group["n"].astype(float)
            total = float(counts.sum())
            probs = counts / total if total else counts
            row: dict[str, object] = {}
            if by_cohort:
                row["cohort"] = key if isinstance(key, str) else key[0]
            row.update({
                "template_entropy_bits": float(-(probs * probs.map(math.log2)).sum()) if total else 0.0,
                "top_template_share": float(counts.iloc[0] / total) if total else 0.0,
                "template_observations": int(total),
            })
            entropy_rows.append(row)
        if entropy_rows:
            entropy_frame = pd.DataFrame(entropy_rows)
            if by_cohort:
                rows = rows.merge(entropy_frame, on=group_cols, how="left")
            else:
                for column in ("template_entropy_bits", "top_template_share", "template_observations"):
                    rows[column] = entropy_frame.iloc[0][column]
        rows.insert(0, "population_scope", "cohort" if by_cohort else "overall")
        return rows

    overall = pd.concat([summary_rows(name, relation) for name, relation in populations], ignore_index=True)
    cohorts = pd.concat([summary_rows(name, relation, by_cohort=True) for name, relation in populations], ignore_index=True)
    locations = summary_rows("distinct_primary", "reps", by_cohort=False)
    location_df = con.execute(f"""
      SELECT location_class, COUNT(*)::BIGINT AS n_units,
             COUNT(DISTINCT file_sha)::BIGINT AS n_distinct_contents,
             MEDIAN(body_chars) AS body_chars_median,
             MEDIAN(n_headings) AS headings_median,
             AVG((n_tables > 0)::INT)::DOUBLE AS has_table_share,
             AVG((n_code_blocks > 0)::INT)::DOUBLE AS has_code_block_share,
             COUNT(DISTINCT template_signature)::BIGINT AS n_unique_templates
      FROM reps
      GROUP BY 1 ORDER BY n_units DESC, location_class
    """).df()
    location_df.insert(0, "population_scope", "location_stratum")

    overall.to_csv(out_dir / "sensitivity_overall.csv", index=False)
    cohorts.to_csv(out_dir / "sensitivity_cohort.csv", index=False)
    location_df.to_csv(out_dir / "location_strata.csv", index=False)
    summary = {
        "run_id": args.run_id,
        "structure_version": STRUCTURE_VERSION,
        "repo_cap": args.repo_cap,
        "cohorts": COHORTS,
        "copy_inclusive_definition": "all artifact rows joined to one structural row per file_sha; cohort and flags come from the representative",
        "outputs": ["sensitivity_overall.csv", "sensitivity_cohort.csv", "location_strata.csv"],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(overall.to_string(index=False))
    print(f"Wrote {out_dir}")
    con.close()


if __name__ == "__main__":
    main()
