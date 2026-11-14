#!/usr/bin/env python3
"""E3-r01 Step 7: template concentration and sampled structural similarity."""
from __future__ import annotations

import argparse
import difflib
import json
import math
from itertools import combinations
from pathlib import Path

import duckdb
import pandas as pd

from gitskills.config import OUT_DIR
from gitskills.structure import STRUCTURE_VERSION


COHORTS = [
    "2025-10", "2025-11", "2025-12", "2026-01", "2026-02",
    "2026-03", "2026-04", "2026-05", "2026-06", "2026-07",
]


def feature_set(row: pd.Series) -> set[str]:
    frontmatter_keys = [] if row.frontmatter_keys is None else list(row.frontmatter_keys)
    heading_levels = [] if row.heading_levels is None else list(row.heading_levels)
    block_sequence = [] if row.block_sequence is None else list(row.block_sequence)
    values = {f"fm:{x}" for x in frontmatter_keys}
    values.update(f"level:{x}" for x in heading_levels)
    values.update(f"block:{x}" for x in block_sequence)
    for name in ("n_bullet_lists", "n_ordered_lists", "n_blockquotes", "n_tables", "n_code_blocks", "n_inline_code", "n_thematic_breaks"):
        if int(getattr(row, name)) > 0:
            values.add(f"feature:{name}")
    return values


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default="E3-r01-primary")
    ap.add_argument("--features", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--sample-per-cohort", type=int, default=25)
    args = ap.parse_args()
    if args.sample_per_cohort < 2:
        raise SystemExit("--sample-per-cohort must be at least 2")
    features = args.features or OUT_DIR / "runs" / args.run_id / "structural_features.parquet"
    out_dir = args.out_dir or OUT_DIR / "runs" / args.run_id / "step7_concentration_similarity"
    out_dir.mkdir(parents=True, exist_ok=True)
    f = str(features).replace("\\", "/")
    cohort_sql = "(" + ",".join("'" + c + "'" for c in COHORTS) + ")"
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    base = f"read_parquet('{f}')"

    counts = con.execute(f"""
      SELECT cohort, template_signature, COUNT(*)::BIGINT AS n
      FROM {base}
      WHERE cohort IN {cohort_sql} AND template_signature IS NOT NULL
      GROUP BY 1, 2 ORDER BY 1, n DESC, template_signature
    """).df()
    concentration_rows: list[dict[str, object]] = []
    entropy_rows: list[dict[str, object]] = []
    for cohort, group in counts.groupby("cohort", sort=True):
        total = int(con.execute(f"SELECT COUNT(*) FROM {base} WHERE cohort = ?", [cohort]).fetchone()[0])
        vals = group.n.astype(float)
        probs = vals / total
        entropy = float(-(probs * probs.map(math.log2)).sum())
        entropy_rows.append({
            "cohort": cohort,
            "n_skills": total,
            "n_unique_templates": int(len(group)),
            "template_entropy_bits": entropy,
            "effective_template_count": 2 ** entropy,
            "top_template_share": float(vals.iloc[0] / total),
        })
        for k in [1, 5, 10, 20, 50, 100, 200, 500, 1000]:
            concentration_rows.append({
                "cohort": cohort,
                "top_k_templates": k,
                "skills_covered": int(vals.head(k).sum()),
                "share": float(vals.head(k).sum() / total),
            })
    entropy_df = pd.DataFrame(entropy_rows)
    concentration_df = pd.DataFrame(concentration_rows)
    entropy_df.to_csv(out_dir / "cohort_concentration.csv", index=False)
    concentration_df.to_csv(out_dir / "cohort_top_template_coverage.csv", index=False)
    counts.to_csv(out_dir / "cohort_template_counts.csv", index=False)

    # Equal-sized, deterministic samples. Ordering by file_sha hash avoids any
    # dependence on Parquet row order while keeping identifiers out of outputs.
    sample_n = min(args.sample_per_cohort, int(entropy_df.n_skills.min()))
    sample = con.execute(f"""
      SELECT * EXCLUDE (file_sha)
      FROM {base}
      WHERE cohort IN {cohort_sql}
      QUALIFY ROW_NUMBER() OVER (PARTITION BY cohort ORDER BY md5(file_sha)) <= {sample_n}
      ORDER BY cohort
    """).df()
    con.close()
    sample_groups = {}
    for cohort, group in sample.groupby("cohort", sort=True):
        records = []
        for row in group.itertuples(index=False):
            row_dict = row._asdict()
            records.append((
                feature_set(pd.Series(row_dict)),
                [] if row.block_sequence is None else list(row.block_sequence),
                row.template_signature,
            ))
        sample_groups[cohort] = records
    pair_rows: list[dict[str, object]] = []
    for left_name, right_name in combinations(COHORTS, 2):
        left = sample_groups[left_name]
        right = sample_groups[right_name]
        scores: list[tuple[float, float, float]] = []
        for lfeatures, lsequence, ltemplate in left:
            for rfeatures, rsequence, rtemplate in right:
                scores.append((
                    1.0 if ltemplate == rtemplate else 0.0,
                    jaccard(lfeatures, rfeatures),
                    difflib.SequenceMatcher(None, lsequence, rsequence, autojunk=False).ratio(),
                ))
        score_df = pd.DataFrame(scores, columns=["exact_template_match", "feature_jaccard", "block_sequence_ratio"])
        pair_rows.append({
            "left_cohort": left_name,
            "right_cohort": right_name,
            "n_left": len(left),
            "n_right": len(right),
            "pair_count": len(score_df),
            "exact_template_match_rate": float(score_df.exact_template_match.mean()),
            "feature_jaccard_mean": float(score_df.feature_jaccard.mean()),
            "feature_jaccard_median": float(score_df.feature_jaccard.median()),
            "block_sequence_ratio_mean": float(score_df.block_sequence_ratio.mean()),
            "block_sequence_ratio_median": float(score_df.block_sequence_ratio.median()),
        })
    pairwise = pd.DataFrame(pair_rows)
    pairwise.to_csv(out_dir / "equal_sample_pairwise_similarity.csv", index=False)

    summary = {
        "run_id": args.run_id,
        "structure_version": STRUCTURE_VERSION,
        "cohorts": COHORTS,
        "sample_per_cohort_requested": args.sample_per_cohort,
        "sample_per_cohort_used": sample_n,
        "sample_selection": "deterministic lowest md5(file_sha) values within each cohort; identifiers discarded before output",
        "pairwise_comparisons": len(pairwise),
        "pairwise_metrics": {
            "exact_template_match_rate": "share of cross-cohort pairs with identical template_signature",
            "feature_jaccard": "Jaccard similarity over anonymized front-matter-key, heading-level, block-sequence, and positive block-feature sets",
            "block_sequence_ratio": "difflib sequence ratio over block-type sequences",
        },
        "outputs": ["cohort_concentration.csv", "cohort_top_template_coverage.csv", "cohort_template_counts.csv", "equal_sample_pairwise_similarity.csv"],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(entropy_df.to_string(index=False))
    print(f"sample_per_cohort={sample_n} pairwise_comparisons={len(pairwise)}")
    print(f"Wrote {out_dir}")


if __name__ == "__main__":
    main()
