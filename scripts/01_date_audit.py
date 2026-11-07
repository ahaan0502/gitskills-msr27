#!/usr/bin/env python3
"""E0 Gate A: which dates exist, and for how much of the data?

Reads the artifacts and repos Parquet via DuckDB (out-of-core) and writes a Markdown
report plus CSV tables to outputs/date_audit/. Column names follow the dataset card;
if a column is missing the script says which one.

    python scripts/01_date_audit.py                 # uses data/raw
    python scripts/01_date_audit.py --raw path/to/parquet_root
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gitskills.config import COLLECTION_END, FORMAT_START, OUT_DIR, RAW_DIR  # noqa: E402

REQUIRED = ["repo_full_name", "path", "filename", "location_class", "file_sha", "dedup_primary",
            "first_commit_at", "last_commit_at", "history_fetched"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--out", type=Path, default=OUT_DIR / "date_audit")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    art_glob = str(args.raw / "artifacts" / "*.parquet")
    repo_glob = str(args.raw / "repos" / "*.parquet")
    con.execute(f"CREATE VIEW artifacts AS SELECT * FROM read_parquet('{art_glob}')")
    con.execute(f"CREATE VIEW repos AS SELECT * FROM read_parquet('{repo_glob}')")

    cols = {r[0] for r in con.execute("DESCRIBE artifacts").fetchall()}
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        sys.exit(f"artifacts is missing expected columns: {missing}\nFound: {sorted(cols)}")

    # Representatives only: they are the only rows with text and history.
    con.execute(f"""
        CREATE VIEW reps AS
        SELECT a.*, TRY_CAST(a.first_commit_at AS TIMESTAMP) AS fc,
               TRY_CAST(r.created_at AS TIMESTAMP) AS repo_created
        FROM artifacts a LEFT JOIN repos r ON r.full_name = a.repo_full_name
        WHERE a.dedup_primary = 1
    """)

    queries = {
        "coverage_by_location": """
            SELECT location_class, COUNT(*) AS distinct_contents,
                   SUM((history_fetched = 1)::INT) AS with_history,
                   ROUND(100.0 * SUM((history_fetched = 1)::INT) / COUNT(*), 1) AS pct_with_history
            FROM reps GROUP BY 1 ORDER BY 2 DESC""",
        "date_validity": f"""
            SELECT CASE
                     WHEN fc IS NULL THEN 'no_date'
                     WHEN fc < TIMESTAMP '{FORMAT_START}' THEN 'before_format'
                     WHEN fc > TIMESTAMP '{COLLECTION_END} 23:59:59' THEN 'after_collection'
                     ELSE 'in_window' END AS bucket,
                   COUNT(*) AS n
            FROM reps GROUP BY 1 ORDER BY 2 DESC""",
        "monthly_cohorts": f"""
            SELECT strftime(date_trunc('month', fc), '%Y-%m') AS cohort, COUNT(*) AS distinct_contents,
                   COUNT(DISTINCT repo_full_name) AS repos
            FROM reps
            WHERE fc BETWEEN TIMESTAMP '{FORMAT_START}' AND TIMESTAMP '{COLLECTION_END} 23:59:59'
            GROUP BY 1 ORDER BY 1""",
        "born_with_repo": f"""
            SELECT ROUND(100.0 * SUM((date_diff('day', repo_created, fc) <= 1)::INT) / COUNT(*), 1)
                   AS pct_first_commit_within_1d_of_repo_creation, COUNT(*) AS n_dated
            FROM reps WHERE fc IS NOT NULL AND repo_created IS NOT NULL""",
        "filename_exactness": """
            SELECT (filename = 'SKILL.md') AS exact_SKILL_md, COUNT(*) AS n FROM reps GROUP BY 1""",
    }

    report = ["# E0 Gate A: date audit\n"]
    for name, sql in queries.items():
        df = con.execute(sql).df()
        df.to_csv(args.out / f"{name}.csv", index=False)
        report.append(f"## {name}\n\n{df.to_markdown(index=False)}\n")
        print(f"--- {name}\n{df.to_string(index=False)}\n")

    (args.out / "date_audit.md").write_text("\n".join(report))
    print(f"Wrote {args.out / 'date_audit.md'}")


if __name__ == "__main__":
    main()
