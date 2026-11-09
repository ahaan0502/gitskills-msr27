#!/usr/bin/env python3
"""Convert the GitSkills SQLite sample into the Parquet mirror layout.

The output is data/sample_parquet/<table>/part-00000.parquet, so the existing
DuckDB audits can read it with the same table globs used for the HF mirror.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sqlite", type=Path, help="SQLite sample or extracted .db path")
    ap.add_argument("--out", type=Path, default=Path("data/sample_parquet"))
    ap.add_argument("--tables", nargs="+", default=None,
                    help="Tables to convert (default: every user table)")
    ap.add_argument("--chunksize", type=int, default=100_000)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.sqlite) as con:
        available = [row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )]
        tables = args.tables or available
        missing = sorted(set(tables) - set(available))
        if missing:
            raise SystemExit(f"SQLite table(s) not found: {missing}; available: {available}")

        for table in tables:
            out_dir = args.out / table
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "part-00000.parquet"
            if out_path.exists():
                out_path.unlink()
            # Identifiers cannot be parameters, so validate them against sqlite_master first.
            query = f'SELECT * FROM "{table.replace(chr(34), chr(34) * 2)}"'
            writer = None
            row_count = 0
            for frame in pd.read_sql_query(query, con, chunksize=args.chunksize):
                table_arrow = pa.Table.from_pandas(frame, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(out_path, table_arrow.schema, compression="zstd")
                writer.write_table(table_arrow)
                row_count += len(frame)
            if writer is None:
                # Preserve an empty table's schema.
                frame = pd.read_sql_query(query + " LIMIT 0", con)
                pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), out_path,
                               compression="zstd")
            else:
                writer.close()
            print(f"{table}: {row_count} row(s) -> {out_path}")


if __name__ == "__main__":
    main()
