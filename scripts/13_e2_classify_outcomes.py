#!/usr/bin/env python3
"""E2 step 4: derive representative-level authorship outcome columns."""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from gitskills.config import OUT_DIR


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skills", type=Path, default=OUT_DIR / "skills.parquet")
    ap.add_argument("--evidence", type=Path, default=OUT_DIR / "e2_authorship_evidence.parquet")
    ap.add_argument("--out", type=Path, default=OUT_DIR / "e2_authorship_classifications.parquet")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    if args.out.exists() and not args.overwrite:
        raise SystemExit(f"Output exists; pass --overwrite to replace it: {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    skills = str(args.skills).replace("\\", "/")
    evidence = str(args.evidence).replace("\\", "/")
    out = str(args.out).replace("\\", "/")
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"""
      COPY (
        WITH evidence_flags AS (
          SELECT file_sha,
                 MAX(CASE WHEN event_position IN ('first', 'first_and_last')
                           AND (author_type_category = 'automated'
                                OR identity_specificity = 'high'
                                OR message_specificity = 'high'
                                OR content_specificity = 'high') THEN 1 ELSE 0 END) AS creation_positive,
                 MAX(CASE WHEN event_position IN ('last', 'first_and_last')
                           AND (author_type_category = 'automated'
                                OR identity_specificity = 'high'
                                OR message_specificity = 'high'
                                OR content_specificity = 'high') THEN 1 ELSE 0 END) AS maintenance_positive,
                 MAX(CASE WHEN author_type_category = 'automated'
                                OR identity_specificity = 'high'
                                OR message_specificity = 'high'
                                OR content_specificity = 'high' THEN 1 ELSE 0 END) AS maintenance_any_positive,
                 MIN(CASE WHEN event_position IN ('first', 'first_and_last') THEN event_date END) AS first_event_date,
                 MAX(CASE WHEN event_position IN ('last', 'first_and_last') THEN event_date END) AS last_event_date,
                 MAX(commit_count) AS commit_count,
                 MAX(history_quality) AS history_quality
          FROM read_parquet('{evidence}')
          GROUP BY file_sha
        ), joined AS (
          SELECT s.file_sha, e.first_event_date, e.last_event_date, e.commit_count,
                 e.history_quality, e.creation_positive, e.maintenance_positive,
                 e.maintenance_any_positive
          FROM read_parquet('{skills}') s
          LEFT JOIN evidence_flags e USING (file_sha)
        ), outcomes AS (
          SELECT *,
            CASE WHEN history_quality IS NULL THEN NULL
                 ELSE creation_positive = 1 END AS creation_agent_explicit,
            CASE WHEN history_quality IS NULL THEN NULL
                 ELSE maintenance_positive = 1 END AS maintenance_agent_explicit,
            CASE WHEN history_quality IS NULL THEN NULL
                 ELSE maintenance_any_positive = 1 END AS maintenance_agent_any_event,
            history_quality IS NULL AS authorship_unknown,
            CASE WHEN history_quality IS NULL THEN 'unknown_history'
                 WHEN creation_positive = 1 AND maintenance_positive = 1 THEN 'agent_created_and_maintained'
                 WHEN creation_positive = 1 THEN 'agent_created_only'
                 WHEN maintenance_positive = 1 THEN 'agent_maintained_only'
                 ELSE 'no_explicit_agent_evidence' END AS authorship_class_lower
          FROM joined
        )
        SELECT file_sha, first_event_date, last_event_date, commit_count, history_quality,
               creation_agent_explicit, maintenance_agent_explicit, maintenance_agent_any_event,
               authorship_unknown, authorship_class_lower,
               CAST(NULL AS VARCHAR) AS creation_human_like,
               CAST(NULL AS VARCHAR) AS maintenance_human_like,
               CAST(NULL AS VARCHAR) AS authorship_class_expanded,
               CAST(NULL AS VARCHAR) AS authorship_class_upper,
               'lower_bound_explicit_markers_only' AS classification_status
        FROM outcomes
      ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    summary = con.execute(f"""
      SELECT authorship_class_lower, COUNT(*) AS n
      FROM read_parquet('{out}') GROUP BY 1 ORDER BY 1
    """).df()
    print(summary.to_string(index=False))
    print(f"Wrote {args.out}")
    con.close()


if __name__ == "__main__":
    main()
