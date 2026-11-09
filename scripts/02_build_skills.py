#!/usr/bin/env python3
"""Parse one representative per distinct GitSkills content hash.

The input is streamed from DuckDB and parsed in independent batches so the full
dataset is never loaded into one Python list. The output is an ignored Parquet
file containing ``file_sha`` plus the flat parser record.
"""
from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gitskills.config import OUT_DIR, RAW_DIR  # noqa: E402
from gitskills.parse import parse_skill  # noqa: E402


def _parse_one(item: tuple[str, str | None]) -> dict[str, Any]:
    file_sha, content = item
    return {"file_sha": file_sha, **parse_skill(content)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--out", type=Path, default=OUT_DIR / "skills.parquet")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--batch-size", type=int, default=5_000)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    if args.workers < 1 or args.batch_size < 1:
        raise SystemExit("--workers and --batch-size must be positive")
    if args.out.exists() and not args.overwrite:
        raise SystemExit(f"Output exists; pass --overwrite to replace it: {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        args.out.unlink()

    art_glob = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    con = duckdb.connect()
    query = f"""
        SELECT file_sha, content
        FROM read_parquet('{art_glob}')
        WHERE dedup_primary = 1
    """
    con.execute(query)
    writer: pq.ParquetWriter | None = None
    schema: pa.Schema | None = None
    total = 0
    pool_context = ProcessPoolExecutor(max_workers=args.workers) if args.workers > 1 else None
    try:
        while True:
            batch = con.fetchmany(args.batch_size)
            if not batch:
                break
            items = [(row[0], row[1]) for row in batch]
            records = (list(pool_context.map(_parse_one, items)) if pool_context is not None
                       else [_parse_one(item) for item in items])
            table = pa.Table.from_pylist(records) if schema is None else pa.Table.from_pylist(records, schema=schema)
            if writer is None:
                writer = pq.ParquetWriter(args.out, table.schema, compression="zstd")
                schema = table.schema
            writer.write_table(table)
            total += len(records)
            print(f"parsed {total:,} representatives", flush=True)
    finally:
        if pool_context is not None:
            pool_context.shutdown()
        if writer is not None:
            writer.close()
    if writer is None:
        raise SystemExit("No representatives found")
    print(f"Wrote {args.out} ({total:,} representatives)")


if __name__ == "__main__":
    main()
