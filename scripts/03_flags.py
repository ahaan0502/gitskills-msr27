#!/usr/bin/env python3
"""Add E0 selection signals to the parsed skill table.

Signals are intentionally separate rather than combined into one exclusion rule:

* ``catalog_flag``: repository/path names contain catalog or marketplace markers.
* ``template_flag``: the normalized content hash is reused across the configured
  number of distinct repositories.
* ``bulk_repo_flag``: a repository contains at least the configured number of
  discovered skill files.
* ``repo_rank``: deterministic order within a repository for later per-repo caps.

These are screening signals, not claims that a skill is actually a catalog,
template, or bulk-generated artifact.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import shutil
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gitskills.config import OUT_DIR, RAW_DIR


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--skills", type=Path, default=OUT_DIR / "skills.parquet")
    ap.add_argument("--out", type=Path, default=OUT_DIR / "skills_flags.parquet")
    ap.add_argument("--template-min-repos", type=int, default=5)
    ap.add_argument("--bulk-repo-min-skills", type=int, default=50)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    if args.template_min_repos < 2 or args.bulk_repo_min_skills < 1:
        raise SystemExit("invalid signal threshold")
    if not args.skills.exists():
        raise SystemExit(f"Missing parsed skills table: {args.skills}")
    if args.out.exists() and not args.overwrite:
        raise SystemExit(f"Output exists; pass --overwrite to replace it: {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        args.out.unlink()

    con = duckdb.connect()
    temp_dir = Path(tempfile.mkdtemp(prefix="gitskills-duckdb-"))
    art = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    skills = str(args.skills).replace("\\", "/")
    out = str(args.out).replace("\\", "/")
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"SET temp_directory='{str(temp_dir).replace(chr(92), '/')}'")
    con.execute(f"""
        COPY (
            WITH occurrence_counts AS (
                SELECT repo_full_name, COUNT(*) AS repo_skill_count
                FROM read_parquet('{art}')
                GROUP BY repo_full_name
            ),
            repo_copies AS (
                SELECT s.norm_hash, COUNT(DISTINCT a.repo_full_name) AS norm_repo_count
                FROM read_parquet('{skills}') s
                JOIN read_parquet('{art}') a USING (file_sha)
                GROUP BY s.norm_hash
            ),
            representatives AS (
                SELECT s.*,
                       a.repo_full_name,
                       a.path,
                       a.location_class,
                       a.filename,
                       row_number() OVER (
                           PARTITION BY a.repo_full_name
                           ORDER BY a.path, s.file_sha
                       ) AS repo_rank,
                       oc.repo_skill_count,
                       COALESCE(rc.norm_repo_count, 0) AS norm_repo_count
                FROM read_parquet('{skills}') s
                JOIN read_parquet('{art}') a USING (file_sha)
                JOIN occurrence_counts oc USING (repo_full_name)
                LEFT JOIN repo_copies rc USING (norm_hash)
                WHERE a.dedup_primary = 1
            )
            SELECT *,
                   regexp_matches(
                       lower(repo_full_name || '/' || path),
                       '(catalog|marketplace|registry|skill[-_ ]?library|awesome[-_ ]?skills)'
                   ) AS catalog_flag,
                   norm_repo_count >= {args.template_min_repos} AS template_flag,
                   repo_skill_count >= {args.bulk_repo_min_skills} AS bulk_repo_flag
            FROM representatives
        ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    try:
        row_count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{out}')").fetchone()[0]
        print(f"Wrote {args.out} ({row_count:,} rows)")
        print(con.execute(f"""
            SELECT COUNT(*) AS n,
                   SUM(catalog_flag::INT) AS catalog,
                   SUM(template_flag::INT) AS template,
                   SUM(bulk_repo_flag::INT) AS bulk_repo
            FROM read_parquet('{out}')
        """).fetchone())
    finally:
        con.close()
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
