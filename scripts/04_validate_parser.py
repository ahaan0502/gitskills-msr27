#!/usr/bin/env python3
"""Validate parser fields against the dataset's parsed representative fields."""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Any

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gitskills.config import OUT_DIR, RAW_DIR  # noqa: E402
from gitskills.parse import parse_skill  # noqa: E402


FIELDS = ("spec_valid", "name", "description", "body_chars")


def _same_bool(value: Any, expected: bool) -> bool:
    if value is None:
        return expected is False
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"0", "false", "f", "no", "n", ""}:
            return expected is False
        if normalized in {"1", "true", "t", "yes", "y"}:
            return expected is True
    return bool(value) is expected


def _same_text(actual: Any, expected: Any) -> bool:
    if actual is None or (isinstance(actual, float) and math.isnan(actual)):
        actual = None
    if expected is None or (isinstance(expected, float) and math.isnan(expected)):
        expected = None
    if isinstance(actual, str):
        actual = actual.strip() or None
    if isinstance(expected, str):
        expected = expected.strip() or None
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return actual == expected
    return actual == expected if actual is None or expected is None else str(actual) == str(expected)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--out", type=Path, default=OUT_DIR / "validation")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    art_glob = str(args.raw / "artifacts" / "*.parquet").replace("\\", "/")
    cols = {r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{art_glob}')").fetchall()}
    required = {"dedup_primary", "content", "frontmatter_valid", "name", "description", "body_chars"}
    missing = sorted(required - cols)
    if missing:
        raise SystemExit(f"artifacts is missing validation columns: {missing}; found: {sorted(cols)}")

    key_cols = [c for c in ("file_sha", "repo_full_name", "path", "artifact_id") if c in cols]
    select = ", ".join(key_cols + ["content", "frontmatter_valid", "name", "description", "body_chars"])
    rows = con.execute(
        f"SELECT {select} FROM read_parquet('{art_glob}') WHERE dedup_primary = 1"
    ).fetchall()
    names = [d[0] for d in con.description]
    disagreements: list[dict[str, Any]] = []
    counts = {field: 0 for field in FIELDS}
    recovered_count = 0
    total = len(rows)
    for values in rows:
        row = dict(zip(names, values))
        parsed = parse_skill(row["content"])
        recovered_count += int(parsed["fm_recovered"])
        # The published body_chars includes the separator newline after front matter.
        separator_chars = 0
        if parsed["has_frontmatter"]:
            separator_chars = 2 if "\r\n" in row["content"] else 1
        body_chars = parsed["body_chars"] + separator_chars
        checks = {
            "spec_valid": _same_bool(row["frontmatter_valid"], parsed["spec_valid"]),
            # Recovery deliberately exposes useful values when the dataset leaves
            # invalid YAML fields empty; those rows are counted as compatible here
            # and reported separately below.
            "name": parsed["fm_recovered"] or _same_text(row["name"], parsed["fm_name"]),
            "description": parsed["fm_recovered"] or _same_text(row["description"], parsed["fm_description"]),
            "body_chars": _same_text(row["body_chars"], body_chars),
        }
        for field, ok in checks.items():
            counts[field] += int(ok)
        if not all(checks.values()):
            disagreements.append({
                **{key: row.get(key) for key in key_cols},
                **{f"dataset_{field}": row[field] for field in ("frontmatter_valid", "name", "description", "body_chars")},
                "parser_spec_valid": parsed["spec_valid"],
                "parser_name": parsed["fm_name"],
                "parser_description": parsed["fm_description"],
                "parser_body_chars_compatible": body_chars,
                "parser_frontmatter_valid": parsed["frontmatter_valid"],
                "parser_fm_recovered": parsed["fm_recovered"],
                "parse_error": parsed["parse_error"],
                "failed_checks": ",".join(field for field, ok in checks.items() if not ok),
            })

    rates = {field: (counts[field] / total if total else 1.0) for field in FIELDS}
    (args.out / "agreement_rates.csv").write_text(
        "field,n_agree,n_total,agreement_rate\n" +
        "".join(f"{field},{counts[field]},{total},{rates[field]:.6f}\n" for field in FIELDS),
        encoding="utf-8",
    )
    disagreement_path = args.out / "disagreements.csv"
    columns = list(disagreements[0]) if disagreements else key_cols + ["failed_checks"]
    with disagreement_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(disagreements)
    print(f"Representatives: {total}")
    for field in FIELDS:
        print(f"{field}: {counts[field]}/{total} = {rates[field]:.3%}")
    print(f"YAML-recovered representatives: {recovered_count}")
    print(f"Disagreements: {len(disagreements)} -> {disagreement_path}")


if __name__ == "__main__":
    main()
