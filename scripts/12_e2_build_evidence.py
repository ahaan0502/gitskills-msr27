#!/usr/bin/env python3
"""E2 step 3: build anonymized first/last commit evidence rows."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gitskills.config import OUT_DIR, RAW_DIR  # noqa: E402
from gitskills.e2_markers import author_type_marker, marker_matches  # noqa: E402


SCHEMA = pa.schema([
    ("file_sha", pa.string()),
    ("event_position", pa.string()),
    ("event_date", pa.string()),
    ("commit_count", pa.int64()),
    ("history_quality", pa.string()),
    ("author_type_category", pa.string()),
    ("identity_marker", pa.bool_()),
    ("identity_specificity", pa.string()),
    ("identity_reasons", pa.string()),
    ("message_marker", pa.bool_()),
    ("message_specificity", pa.string()),
    ("message_reasons", pa.string()),
    ("content_marker", pa.bool_()),
    ("content_specificity", pa.string()),
    ("content_reasons", pa.string()),
])


def _evidence(author_type: object, author: object, message: object, content: object) -> dict[str, object]:
    type_match = author_type_marker(author_type)
    identity = marker_matches(author, "identity")
    if type_match:
        identity = [type_match, *identity]
    message_matches = marker_matches(message, "message")
    content_matches = marker_matches(content, "content")

    def summarize(matches: list[dict[str, str]]) -> tuple[bool, str | None, str]:
        if not matches:
            return False, None, ""
        rank = {"high": 0, "medium": 1, "low": 2}
        strongest = min(matches, key=lambda item: rank[item["specificity"]])["specificity"]
        return True, strongest, ",".join(sorted({item["reason_code"] for item in matches}))

    identity_flag, identity_spec, identity_reasons = summarize(identity)
    message_flag, message_spec, message_reasons = summarize(message_matches)
    content_flag, content_spec, content_reasons = summarize(content_matches)
    if type_match and type_match["reason_code"] == "author_type_automated":
        type_category = "automated"
    elif type_match and type_match["reason_code"] == "author_type_non_automated":
        type_category = "non_automated_category"
    else:
        type_category = "unknown"
    return {
        "author_type_category": type_category,
        "identity_marker": identity_flag,
        "identity_specificity": identity_spec,
        "identity_reasons": identity_reasons,
        "message_marker": message_flag,
        "message_specificity": message_spec,
        "message_reasons": message_reasons,
        "content_marker": content_flag,
        "content_specificity": content_spec,
        "content_reasons": content_reasons,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--skills", type=Path, default=OUT_DIR / "skills.parquet")
    ap.add_argument("--out", type=Path, default=OUT_DIR / "e2_authorship_evidence.parquet")
    ap.add_argument("--batch-size", type=int, default=5_000)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    if args.out.exists() and not args.overwrite:
        raise SystemExit(f"Output exists; pass --overwrite to replace it: {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        args.out.unlink()

    raw = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    skills = str(args.skills).replace("\\", "/")
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"""
        SELECT a.file_sha,
               a.first_commit_at, a.last_commit_at, a.commit_count,
               a.first_commit_author, a.last_commit_author,
               a.first_commit_author_type, a.last_commit_author_type,
               a.first_commit_message, a.last_commit_message,
               s.fm_description, s.body_prose
        FROM read_parquet('{raw}') a
        LEFT JOIN read_parquet('{skills}') s USING (file_sha)
        WHERE a.dedup_primary = 1
          AND a.history_fetched = 1
          AND a.first_commit_at IS NOT NULL
          AND a.last_commit_at IS NOT NULL
    """)
    writer: pq.ParquetWriter | None = None
    total = 0
    try:
        while True:
            rows = con.fetchmany(args.batch_size)
            if not rows:
                break
            records: list[dict[str, object]] = []
            for row in rows:
                (file_sha, first_date, last_date, commit_count, first_author, last_author,
                 first_type, last_type, first_message, last_message, description, body) = row
                content = f"{description or ''}\n{body or ''}"
                single = (commit_count is not None and int(commit_count) <= 1) or (
                    first_date == last_date and first_author == last_author and first_message == last_message
                )
                positions = [("first_and_last", first_date, first_author, first_type, first_message)] if single else [
                    ("first", first_date, first_author, first_type, first_message),
                    ("last", last_date, last_author, last_type, last_message),
                ]
                quality = "single_commit_or_same_endpoints" if single else "first_last_only_no_middle_events"
                for position, date, author, author_type, message in positions:
                    record = _evidence(author_type, author, message, content)
                    records.append({
                        "file_sha": file_sha,
                        "event_position": position,
                        "event_date": str(date),
                        "commit_count": int(commit_count) if commit_count is not None else None,
                        "history_quality": quality,
                        **record,
                    })
            table = pa.Table.from_pylist(records, schema=SCHEMA)
            if writer is None:
                writer = pq.ParquetWriter(args.out, SCHEMA, compression="zstd")
            writer.write_table(table)
            total += len(records)
            print(f"wrote {total:,} evidence rows", flush=True)
    finally:
        if writer is not None:
            writer.close()
        con.close()
    if writer is None:
        raise SystemExit("No history rows found")
    print(f"Wrote {args.out} ({total:,} rows)")


if __name__ == "__main__":
    main()
