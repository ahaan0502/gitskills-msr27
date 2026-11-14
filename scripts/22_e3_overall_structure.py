#!/usr/bin/env python3
"""E3-r01 Step 4: compute overall structural distributions."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import duckdb
import pandas as pd

from gitskills.config import OUT_DIR
from gitskills.structure import STRUCTURE_VERSION


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default="E3-r01-primary")
    ap.add_argument("--features", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()
    features = args.features or OUT_DIR / "runs" / args.run_id / "structural_features.parquet"
    out_dir = args.out_dir or OUT_DIR / "runs" / args.run_id / "step4_overall_structure"
    out_dir.mkdir(parents=True, exist_ok=True)
    f = str(features).replace("\\", "/")
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    base = f"read_parquet('{f}')"

    size = con.execute(f"""
      SELECT COUNT(*)::BIGINT AS n_skills,
             AVG(body_chars) AS body_chars_mean, MEDIAN(body_chars) AS body_chars_median,
             QUANTILE_CONT(body_chars, 0.25) AS body_chars_p25, QUANTILE_CONT(body_chars, 0.75) AS body_chars_p75,
             AVG(body_words) AS body_words_mean, MEDIAN(body_words) AS body_words_median,
             QUANTILE_CONT(body_words, 0.25) AS body_words_p25, QUANTILE_CONT(body_words, 0.75) AS body_words_p75,
             AVG(body_lines) AS body_lines_mean, MEDIAN(body_lines) AS body_lines_median,
             AVG(n_paragraphs) AS paragraphs_mean, MEDIAN(n_paragraphs) AS paragraphs_median,
             AVG(n_headings) AS headings_mean, MEDIAN(n_headings) AS headings_median,
             AVG(max_heading_depth) AS max_heading_depth_mean, MEDIAN(max_heading_depth) AS max_heading_depth_median
      FROM {base}
    """).df()
    size.to_csv(out_dir / "size_summary.csv", index=False)

    prevalence = con.execute(f"""
      SELECT metric, n::BIGINT AS n, ROUND(n::DOUBLE / COUNT(*) OVER (), 8) AS share
      FROM (
        SELECT 'structure_ok' AS metric, COUNT(*) FILTER (WHERE structure_status = 'ok') AS n FROM {base}
        UNION ALL SELECT 'parser_error_present', COUNT(*) FILTER (WHERE structure_status = 'parser_error_present') FROM {base}
        UNION ALL SELECT 'symlink_like', COUNT(*) FILTER (WHERE structure_status = 'symlink_like') FROM {base}
        UNION ALL SELECT 'empty', COUNT(*) FILTER (WHERE structure_status = 'empty') FROM {base}
        UNION ALL SELECT 'has_frontmatter_name_key', COUNT(*) FILTER (WHERE has_name_key) FROM {base}
        UNION ALL SELECT 'has_frontmatter_description_key', COUNT(*) FILTER (WHERE has_description_key) FROM {base}
        UNION ALL SELECT 'has_heading', COUNT(*) FILTER (WHERE n_headings > 0) FROM {base}
        UNION ALL SELECT 'has_multiple_headings', COUNT(*) FILTER (WHERE n_headings > 1) FROM {base}
        UNION ALL SELECT 'has_bullet_list', COUNT(*) FILTER (WHERE n_bullet_lists > 0) FROM {base}
        UNION ALL SELECT 'has_ordered_list', COUNT(*) FILTER (WHERE n_ordered_lists > 0) FROM {base}
        UNION ALL SELECT 'has_blockquote', COUNT(*) FILTER (WHERE n_blockquotes > 0) FROM {base}
        UNION ALL SELECT 'has_table', COUNT(*) FILTER (WHERE n_tables > 0) FROM {base}
        UNION ALL SELECT 'has_code_block', COUNT(*) FILTER (WHERE n_code_blocks > 0) FROM {base}
        UNION ALL SELECT 'has_inline_code', COUNT(*) FILTER (WHERE n_inline_code > 0) FROM {base}
        UNION ALL SELECT 'has_thematic_break', COUNT(*) FILTER (WHERE n_thematic_breaks > 0) FROM {base}
      ) metrics, (SELECT COUNT(*) AS total FROM {base}) totals
    """).df()
    prevalence["share"] = prevalence["n"] / int(size.iloc[0]["n_skills"])
    prevalence.to_csv(out_dir / "feature_prevalence.csv", index=False)

    con.execute(f"""
      COPY (
        SELECT section_name, COUNT(*)::BIGINT AS occurrences,
               COUNT(DISTINCT file_sha)::BIGINT AS skills
        FROM {base} CROSS JOIN UNNEST(heading_names) AS u(section_name)
        WHERE section_name <> ''
        GROUP BY 1 ORDER BY skills DESC, section_name
        LIMIT 200
      ) TO '{str(out_dir / 'section_frequency.csv').replace(chr(92), '/')}' (FORMAT CSV, HEADER)
    """)
    con.execute(f"""
      COPY (
        SELECT frontmatter_key, COUNT(*)::BIGINT AS skills
        FROM {base} CROSS JOIN UNNEST(frontmatter_keys) AS u(frontmatter_key)
        WHERE frontmatter_key <> ''
        GROUP BY 1 ORDER BY skills DESC, frontmatter_key
        LIMIT 200
      ) TO '{str(out_dir / 'frontmatter_key_frequency.csv').replace(chr(92), '/')}' (FORMAT CSV, HEADER)
    """)
    con.execute(f"""
      COPY (
        SELECT block_type, COUNT(*)::BIGINT AS occurrences
        FROM {base} CROSS JOIN UNNEST(block_sequence) AS u(block_type)
        GROUP BY 1 ORDER BY occurrences DESC, block_type
      ) TO '{str(out_dir / 'block_frequency.csv').replace(chr(92), '/')}' (FORMAT CSV, HEADER)
    """)
    templates = con.execute(f"""
      SELECT template_signature, COUNT(*)::BIGINT AS skills
      FROM {base} WHERE template_signature IS NOT NULL
      GROUP BY 1 ORDER BY skills DESC, template_signature
    """).df()
    templates.to_csv(out_dir / "template_frequency.csv", index=False)
    total = int(size.iloc[0]["n_skills"])
    probs = templates.skills / total
    entropy = float(-(probs * probs.map(math.log2)).sum()) if len(templates) else 0.0
    top_rows = []
    cumulative = 0
    for k in [1, 5, 10, 20, 50, 100, 200, 500, 1000]:
        cumulative = int(templates.head(k).skills.sum())
        top_rows.append({"top_k_templates": k, "skills_covered": cumulative, "share": cumulative / total})
    pd.DataFrame(top_rows).to_csv(out_dir / "template_concentration.csv", index=False)
    summary = {
        "run_id": args.run_id,
        "structure_version": STRUCTURE_VERSION,
        "n_skills": total,
        "n_unique_templates": int(len(templates)),
        "template_entropy_bits": entropy,
        "outputs": [
            "size_summary.csv", "feature_prevalence.csv", "section_frequency.csv",
            "frontmatter_key_frequency.csv", "block_frequency.csv",
            "template_frequency.csv", "template_concentration.csv",
        ],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(prevalence.to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
