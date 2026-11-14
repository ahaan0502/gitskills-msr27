#!/usr/bin/env python3
"""E3-r01 Step 5: compute structural trends across E0-valid cohorts."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import duckdb
import pandas as pd

from gitskills.config import OUT_DIR
from gitskills.structure import STRUCTURE_VERSION


COHORTS = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"]


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if not total:
        return (float("nan"), float("nan"))
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return max(0.0, center - half), min(1.0, center + half)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default="E3-r01-primary")
    ap.add_argument("--features", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()
    features = args.features or OUT_DIR / "runs" / args.run_id / "structural_features.parquet"
    out_dir = args.out_dir or OUT_DIR / "runs" / args.run_id / "step5_cohort_structure"
    out_dir.mkdir(parents=True, exist_ok=True)
    f = str(features).replace("\\", "/")
    cohort_sql = "(" + ",".join("'" + c + "'" for c in COHORTS) + ")"
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    base = f"read_parquet('{f}')"

    size = con.execute(f"""
      SELECT cohort, COUNT(*)::BIGINT AS n_skills,
             AVG(body_chars) AS body_chars_mean, MEDIAN(body_chars) AS body_chars_median,
             AVG(body_words) AS body_words_mean, MEDIAN(body_words) AS body_words_median,
             AVG(n_headings) AS headings_mean, MEDIAN(n_headings) AS headings_median,
             AVG(n_paragraphs) AS paragraphs_mean, MEDIAN(n_paragraphs) AS paragraphs_median
      FROM {base} WHERE cohort IN {cohort_sql}
      GROUP BY 1 ORDER BY 1
    """).df()

    template_counts = con.execute(f"""
      SELECT cohort, template_signature, COUNT(*)::BIGINT AS skills
      FROM {base} WHERE cohort IN {cohort_sql} AND template_signature IS NOT NULL
      GROUP BY 1, 2 ORDER BY 1, 3 DESC
    """).df()
    concentration_rows = []
    entropy_rows = []
    for cohort, group in template_counts.groupby("cohort", sort=True):
        total = int(size.loc[size.cohort == cohort, "n_skills"].iloc[0])
        counts = group.skills.astype(int)
        probs = counts / total
        entropy_rows.append({
            "cohort": cohort,
            "n_unique_templates": int(len(group)),
            "template_entropy_bits": float(-(probs * probs.map(math.log2)).sum()),
            "top_template_share": int(counts.iloc[0]) / total,
        })
        for k in [1, 5, 10, 20, 50, 100, 200, 500]:
            covered = int(counts.head(k).sum())
            concentration_rows.append({"cohort": cohort, "top_k_templates": k, "skills_covered": covered, "share": covered / total})
    size = size.merge(pd.DataFrame(entropy_rows), on="cohort", how="left")
    size.to_csv(out_dir / "cohort_size_and_template_summary.csv", index=False)
    pd.DataFrame(concentration_rows).to_csv(out_dir / "cohort_template_concentration.csv", index=False)
    template_counts.to_csv(out_dir / "cohort_template_frequency.csv", index=False)

    feature_sql = """
        SELECT cohort, metric, n::BIGINT AS n
        FROM (
          SELECT cohort, 'has_heading' AS metric, COUNT(*) FILTER (WHERE n_headings > 0) AS n FROM {base} WHERE cohort IN {cohort_sql} GROUP BY 1
          UNION ALL SELECT cohort, 'has_multiple_headings', COUNT(*) FILTER (WHERE n_headings > 1) FROM {base} WHERE cohort IN {cohort_sql} GROUP BY 1
          UNION ALL SELECT cohort, 'has_bullet_list', COUNT(*) FILTER (WHERE n_bullet_lists > 0) FROM {base} WHERE cohort IN {cohort_sql} GROUP BY 1
          UNION ALL SELECT cohort, 'has_ordered_list', COUNT(*) FILTER (WHERE n_ordered_lists > 0) FROM {base} WHERE cohort IN {cohort_sql} GROUP BY 1
          UNION ALL SELECT cohort, 'has_blockquote', COUNT(*) FILTER (WHERE n_blockquotes > 0) FROM {base} WHERE cohort IN {cohort_sql} GROUP BY 1
          UNION ALL SELECT cohort, 'has_table', COUNT(*) FILTER (WHERE n_tables > 0) FROM {base} WHERE cohort IN {cohort_sql} GROUP BY 1
          UNION ALL SELECT cohort, 'has_code_block', COUNT(*) FILTER (WHERE n_code_blocks > 0) FROM {base} WHERE cohort IN {cohort_sql} GROUP BY 1
          UNION ALL SELECT cohort, 'has_inline_code', COUNT(*) FILTER (WHERE n_inline_code > 0) FROM {base} WHERE cohort IN {cohort_sql} GROUP BY 1
          UNION ALL SELECT cohort, 'has_thematic_break', COUNT(*) FILTER (WHERE n_thematic_breaks > 0) FROM {base} WHERE cohort IN {cohort_sql} GROUP BY 1
        )
    """.format(base=base, cohort_sql=cohort_sql)
    features_df = con.execute(feature_sql).df()
    features_df = features_df.merge(size[["cohort", "n_skills"]], on="cohort", how="left")
    features_df["share"] = features_df["n"] / features_df["n_skills"]
    intervals = features_df.apply(lambda r: wilson(int(r.n), int(r.n_skills)), axis=1)
    features_df["wilson95_low"] = [x[0] for x in intervals]
    features_df["wilson95_high"] = [x[1] for x in intervals]
    features_df.to_csv(out_dir / "cohort_feature_prevalence.csv", index=False)

    summary = {
        "run_id": args.run_id,
        "structure_version": STRUCTURE_VERSION,
        "cohorts": COHORTS,
        "cohort_count": len(COHORTS),
        "other_or_undated_excluded": True,
        "outputs": ["cohort_size_and_template_summary.csv", "cohort_template_concentration.csv", "cohort_template_frequency.csv", "cohort_feature_prevalence.csv"],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(size.to_string(index=False))
    print(features_df.to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
