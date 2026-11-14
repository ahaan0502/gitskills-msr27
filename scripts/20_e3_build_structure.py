#!/usr/bin/env python3
"""E3-r01 Step 2: extract structural features with durable batch outputs."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gitskills.config import OUT_DIR, RAW_DIR  # noqa: E402
from gitskills.structure import STRUCTURE_VERSION, extract_structure  # noqa: E402


def _extract_one(item: tuple[str, str | None, object, str | None, bool, bool, str, str, bool, bool, bool, int | None]) -> dict[str, Any]:
    return extract_structure(*item)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", default="E3-r01-primary")
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--skills", type=Path, default=OUT_DIR / "skills.parquet")
    ap.add_argument("--flags", type=Path, default=OUT_DIR / "skills_flags.parquet")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=5_000)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    if args.workers < 1 or args.batch_size < 1:
        raise SystemExit("--workers and --batch-size must be positive")
    out = args.out or OUT_DIR / "runs" / args.run_id / "structural_features.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    parts_dir = out.parent / f"{out.stem}.parts"
    progress_path = out.parent / f"{out.stem}.progress.json"
    complete_path = out.parent / f"{out.stem}.complete.json"
    log_path = out.parent / f"{out.stem}.run.log"
    if args.overwrite:
        if out.exists():
            out.unlink()
        if parts_dir.exists():
            shutil.rmtree(parts_dir)
        for path in (progress_path, complete_path, log_path):
            if path.exists():
                path.unlink()
    elif out.exists() or complete_path.exists() or parts_dir.exists():
        raise SystemExit("Output state exists; pass --overwrite to restart safely")
    parts_dir.mkdir(parents=True, exist_ok=True)

    def log(message: str) -> None:
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {message}"
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    art = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    skills = str(args.skills).replace("\\", "/")
    flags = str(args.flags).replace("\\", "/")
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"""
      SELECT a.file_sha, a.content, s.fm_keys, s.parse_error, s.is_empty, s.is_symlink_like,
             CASE WHEN TRY_CAST(a.first_commit_at AS TIMESTAMP)
                        BETWEEN TIMESTAMP '2025-10-01' AND TIMESTAMP '2026-07-31 23:59:59'
                  THEN strftime(TRY_CAST(a.first_commit_at AS TIMESTAMP), '%Y-%m')
                  ELSE 'other_or_undated' END AS cohort,
             COALESCE(a.location_class, 'unknown') AS location_class,
             f.catalog_flag, f.template_flag, f.bulk_repo_flag, f.repo_rank
      FROM read_parquet('{art}') a
      JOIN read_parquet('{skills}') s USING (file_sha)
      JOIN read_parquet('{flags}') f USING (file_sha)
      WHERE a.dedup_primary = 1
    """)
    pool = ProcessPoolExecutor(max_workers=args.workers) if args.workers > 1 else None
    total = 0
    batch_number = 0
    started = time.time()
    try:
        while True:
            batch = con.fetchmany(args.batch_size)
            if not batch:
                break
            items = [(r[0], r[1], r[2], r[3], bool(r[4]), bool(r[5]), r[6], r[7], bool(r[8]), bool(r[9]), bool(r[10]), r[11]) for r in batch]
            records = list(pool.map(_extract_one, items)) if pool else [_extract_one(item) for item in items]
            table = pa.Table.from_pylist(records)
            part_path = parts_dir / f"part-{batch_number:06d}.parquet"
            pq.write_table(table, part_path, compression="zstd")
            total += len(records)
            batch_number += 1
            progress = {
                "run_id": args.run_id,
                "structure_version": STRUCTURE_VERSION,
                "status": "running",
                "batches_completed": batch_number,
                "rows_completed": total,
                "last_part": part_path.name,
                "updated_epoch": time.time(),
            }
            progress_path.write_text(json.dumps(progress, indent=2) + "\n", encoding="utf-8")
            log(f"completed batch={batch_number} rows={total:,}")
    except BaseException:
        log(f"interrupted after batches={batch_number} rows={total:,}; completed parts remain durable")
        raise
    finally:
        if pool:
            pool.shutdown()
        con.close()

    temp_final = out.with_suffix(out.suffix + ".tmp")
    if temp_final.exists():
        temp_final.unlink()
    merge_con = duckdb.connect()
    merge_con.execute("SET threads=1")
    parts_glob = str(parts_dir / "part-*.parquet").replace("\\", "/")
    merge_con.execute(f"COPY (SELECT * FROM read_parquet('{parts_glob}')) TO '{str(temp_final).replace(chr(92), '/')}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    check = merge_con.execute(f"SELECT COUNT(*)::BIGINT, COUNT(DISTINCT file_sha)::BIGINT FROM read_parquet('{str(temp_final).replace(chr(92), '/')}' )").fetchone()
    merge_con.close()
    if check != (total, total):
        raise SystemExit(f"final count check failed: rows={check[0]} distinct_file_sha={check[1]} expected={total}")
    temp_final.replace(out)
    complete = {
        "run_id": args.run_id,
        "structure_version": STRUCTURE_VERSION,
        "status": "complete",
        "rows": total,
        "distinct_file_sha": total,
        "batches": batch_number,
        "elapsed_seconds": round(time.time() - started, 2),
        "completed_epoch": time.time(),
    }
    complete_path.write_text(json.dumps(complete, indent=2) + "\n", encoding="utf-8")
    progress_path.write_text(json.dumps(complete, indent=2) + "\n", encoding="utf-8")
    log(f"complete rows={total:,} batches={batch_number} output={out}")


if __name__ == "__main__":
    main()
