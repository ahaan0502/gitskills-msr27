#!/usr/bin/env python3
"""E2 step 1: inventory history and authorship fields without exporting identities."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

from gitskills.config import OUT_DIR, RAW_DIR


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--out", type=Path, default=OUT_DIR / "e2_history_inventory")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    art = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    repos = str(args.raw / "repos" / "*.parquet").replace("\\", "/")
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"CREATE VIEW artifacts AS SELECT * FROM read_parquet('{art}')")
    con.execute(f"CREATE VIEW repos AS SELECT * FROM read_parquet('{repos}')")

    schemas: dict[str, list[dict[str, str]]] = {}
    for name in ("artifacts", "repos"):
        rows = con.execute(f"DESCRIBE {name}").fetchall()
        schemas[name] = [{"column": row[0], "type": row[1], "null": row[2]} for row in rows]
    (args.out / "schema.json").write_text(json.dumps(schemas, indent=2))

    art_cols = [row["column"] for row in schemas["artifacts"]]
    repo_cols = [row["column"] for row in schemas["repos"]]
    reps = "WHERE a.dedup_primary = 1"
    metrics: list[dict[str, object]] = []

    def add_metric(name: str, value: object, denominator: object | None = None) -> None:
        metrics.append({"metric": name, "value": value, "denominator": denominator})

    add_metric("artifact_rows", con.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0])
    add_metric("representative_rows", con.execute(f"SELECT COUNT(*) FROM artifacts a {reps}").fetchone()[0])
    for col in ["history_fetched", "first_commit_at", "last_commit_at"]:
        if col in art_cols:
            n = con.execute(f"SELECT COUNT(*) FROM artifacts a {reps} AND a.{col} IS NOT NULL").fetchone()[0]
            add_metric(f"representatives_with_{col}", n, "representative_rows")
    if "history_fetched" in art_cols:
        n = con.execute(f"SELECT COUNT(*) FROM artifacts a {reps} AND a.history_fetched = 1").fetchone()[0]
        add_metric("representatives_history_fetched_true", n, "representative_rows")
    if all(col in art_cols for col in ["first_commit_author", "last_commit_author"]):
        n = con.execute(f"SELECT COUNT(*) FROM artifacts a {reps} AND a.first_commit_author = a.last_commit_author").fetchone()[0]
        add_metric("first_equals_last_commit_author", n, "representatives_with_first_commit_author")
    if "commit_count" in art_cols:
        row = con.execute(f"SELECT MIN(commit_count), AVG(commit_count), MEDIAN(commit_count), MAX(commit_count) FROM artifacts a {reps} AND a.commit_count IS NOT NULL").fetchone()
        for label, value in zip(("min", "mean", "median", "max"), row):
            add_metric(f"commit_count_{label}", value, "representatives_with_commit_count")

    identity_candidates = [
        "first_commit_author", "last_commit_author", "first_commit_author_name",
        "last_commit_author_name", "first_commit_author_email", "last_commit_author_email",
        "author_name", "author_email", "commit_author", "commit_author_name", "commit_author_email",
    ]
    message_candidates = ["first_commit_message", "last_commit_message", "commit_message", "commit_messages", "messages"]
    history_candidates = ["commit_count", "history", "commits", "commit_history", "commit_dates"]
    for group, candidates in [("identity", identity_candidates), ("message", message_candidates), ("history_detail", history_candidates)]:
        for col in candidates:
            if col in art_cols:
                n = con.execute(f"SELECT COUNT(*) FROM artifacts a {reps} AND a.{col} IS NOT NULL").fetchone()[0]
                add_metric(f"{group}_field_{col}_non_null", n, "representative_rows")
    for col in ["first_commit_author_type", "last_commit_author_type"]:
        if col in art_cols:
            counts = con.execute(f"SELECT COALESCE(CAST(a.{col} AS VARCHAR), '<null>') AS value, COUNT(*) AS n FROM artifacts a {reps} GROUP BY 1 ORDER BY n DESC").fetchall()
            for value, n in counts:
                add_metric(f"{col}={value}", n, "representative_rows")
    if "repo_full_name" in art_cols and "full_name" in repo_cols:
        n = con.execute("SELECT COUNT(*) FROM (SELECT DISTINCT a.repo_full_name FROM artifacts a JOIN repos r ON r.full_name = a.repo_full_name WHERE a.dedup_primary = 1)").fetchone()[0]
        add_metric("distinct_representative_repositories_joined", n, "repo_rows")
    for col in repo_cols:
        if col.lower() in {"full_name", "created_at", "default_branch", "description", "language", "stargazers_count", "forks_count"}:
            n = con.execute(f"SELECT COUNT(*) FROM repos WHERE \"{col}\" IS NOT NULL").fetchone()[0]
            add_metric(f"repo_field_{col}_non_null", n, "repo_rows")
    add_metric("repo_rows", con.execute("SELECT COUNT(*) FROM repos").fetchone()[0])
    pd.DataFrame(metrics).to_csv(args.out / "availability.csv", index=False)
    print(pd.DataFrame(metrics).to_string(index=False))
    print(f"artifact_columns={art_cols}")
    print(f"repo_columns={repo_cols}")
    con.close()
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
