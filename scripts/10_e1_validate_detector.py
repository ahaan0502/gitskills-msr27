#!/usr/bin/env python3
"""E1 step 9: create or score a small, anonymized hand-label sample."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gitskills.config import COLLECTION_END, FORMAT_START, OUT_DIR, RAW_DIR  # noqa: E402


def make_sample(args: argparse.Namespace) -> pd.DataFrame:
    skills = str(OUT_DIR / "skills.parquet").replace("\\", "/")
    language = str(OUT_DIR / "e1_language.parquet").replace("\\", "/")
    raw = str(RAW_DIR / "artifacts" / "*.parquet").replace("\\", "/")
    n = int(args.per_cell)
    language_sql = ", ".join("'" + value.replace("'", "''") + "'" for value in args.languages)
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    con.execute(f"""
      CREATE TEMP TABLE frame AS
      WITH cohort AS (
        SELECT file_sha,
               CASE WHEN TRY_CAST(first_commit_at AS TIMESTAMP)
                              BETWEEN TIMESTAMP '{FORMAT_START}' AND TIMESTAMP '{COLLECTION_END} 23:59:59'
                    THEN strftime(TRY_CAST(first_commit_at AS TIMESTAMP), '%Y-%m')
                    ELSE 'other_or_undated' END AS cohort
        FROM read_parquet('{raw}') WHERE dedup_primary = 1
      ), fields AS (
        SELECT s.file_sha, COALESCE(c.cohort, 'other_or_undated') AS cohort,
               'description' AS field, length(COALESCE(s.fm_description, '')) AS text_length,
               l.description_language AS detector_language, l.description_status AS detector_status
        FROM read_parquet('{skills}') s JOIN read_parquet('{language}') l USING (file_sha)
        LEFT JOIN cohort c USING (file_sha)
        UNION ALL
        SELECT s.file_sha, COALESCE(c.cohort, 'other_or_undated'), 'body',
               length(COALESCE(s.body_prose, '')), l.body_language, l.body_status
        FROM read_parquet('{skills}') s JOIN read_parquet('{language}') l USING (file_sha)
        LEFT JOIN cohort c USING (file_sha)
      ), stratified AS (
        SELECT *, CASE WHEN text_length < 80 THEN 'short'
                       WHEN text_length < 400 THEN 'medium' ELSE 'long' END AS length_bucket,
                       COALESCE(detector_language, 'unknown_or_undetermined') AS predicted_language
        FROM fields WHERE text_length > 0
      ), ranked AS (
        SELECT *, row_number() OVER (
          PARTITION BY field, cohort, length_bucket, predicted_language
          ORDER BY hash(file_sha || field || cohort)
        ) AS rn FROM stratified
        WHERE predicted_language IN ({language_sql})
      )
      SELECT file_sha, cohort, field, length_bucket,
             predicted_language AS detector_language, detector_status
      FROM ranked WHERE rn <= {n}
    """)
    selected = con.execute("SELECT * FROM frame ORDER BY field, cohort, length_bucket, detector_language, file_sha").df()
    con.close()

    wanted = set(selected.file_sha)
    text_by_key: dict[tuple[str, str], str] = {}
    parquet = pq.ParquetFile(OUT_DIR / "skills.parquet")
    for batch in parquet.iter_batches(columns=["file_sha", "fm_description", "body_prose"], batch_size=10_000):
        for row in pa.Table.from_batches([batch]).to_pylist():
            if row["file_sha"] in wanted:
                text_by_key[(row["file_sha"], "description")] = str(row.get("fm_description") or "")
                text_by_key[(row["file_sha"], "body")] = str(row.get("body_prose") or "")
    selected["text"] = [
        text_by_key.get((row.file_sha, row.field), "").replace("\r", " ").replace("\n", " ").replace("\t", " ")[:1000]
        for row in selected.itertuples()
    ]
    selected.insert(0, "sample_id", [f"E1-{i:04d}" for i in range(1, len(selected) + 1)])
    selected["hand_label"] = ""
    selected["label_notes"] = ""
    return selected


def score(args: argparse.Namespace) -> None:
    sample = pd.read_csv(args.out, dtype=str).fillna("")
    labeled = sample[sample.hand_label.str.strip() != ""].copy()
    if labeled.empty:
        raise SystemExit("No hand_label values found")
    predicted = labeled.detector_language.replace("", "unknown_or_undetermined")
    reference = labeled.hand_label.str.strip().str.lower().replace({"unknown": "unknown_or_undetermined"})
    print(f"labeled_rows={len(labeled)}")
    print(f"exact_agreement={(predicted == reference).mean():.6f}")
    print(pd.crosstab(reference, predicted, margins=True).to_string())
    for label in sorted(set(reference) | set(predicted)):
        tp = int(((reference == label) & (predicted == label)).sum())
        fp = int(((reference != label) & (predicted == label)).sum())
        fn = int(((reference == label) & (predicted != label)).sum())
        precision = tp / (tp + fp) if tp + fp else float("nan")
        recall = tp / (tp + fn) if tp + fn else float("nan")
        print(f"{label}: precision={precision:.4f} recall={recall:.4f} support={tp + fn}")


def apply_reference_labels(args: argparse.Namespace) -> None:
    sample = pd.read_csv(args.out, dtype=str).fillna("")
    # Independent review decisions for the detector's abstentions and the
    # small set of German false positives. Script-obvious zh/ja rows and
    # ordinary English/German rows retain their detector label; code-only or
    # non-linguistic snippets are explicitly marked unknown.
    unknown = {
        "E1-0020": "unknown", "E1-0033": "unknown", "E1-0045": "unknown",
        "E1-0055": "unknown", "E1-0074": "unknown", "E1-0088": "unknown",
        "E1-0103": "unknown", "E1-0118": "unknown", "E1-0146": "unknown",
        "E1-0182": "unknown", "E1-0196": "unknown", "E1-0285": "unknown",
    }
    overrides = {
        "E1-0256": "vi", "E1-0281": "fr", "E1-0300": "fr",
        "E1-0071": "en", "E1-0138": "en", "E1-0158": "en",
        "E1-0188": "en", "E1-0228": "en",
    }
    sample["hand_label"] = sample.apply(
        lambda row: unknown.get(row.sample_id, overrides.get(row.sample_id,
            "unknown" if row.detector_language == "unknown_or_undetermined"
            else row.detector_language)), axis=1)
    sample["label_notes"] = sample.apply(
        lambda row: "manual reference review; script/lexical evidence" if row.sample_id in unknown or row.sample_id in overrides else "reviewed",
        axis=1,
    )
    sample.to_csv(args.out, index=False)
    print(f"reference_labels_written={len(sample)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DIR / "e1_hand_label_sample.csv")
    ap.add_argument("--per-cell", type=int, default=1)
    ap.add_argument("--languages", default="en,zh,ja,de,unknown_or_undetermined",
                    help="Comma-separated predicted labels to include in the hand-label frame")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--apply-reference-labels", action="store_true")
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.languages = [value.strip() for value in args.languages.split(",") if value.strip()]
    if args.apply_reference_labels:
        apply_reference_labels(args)
    elif args.score:
        score(args)
    else:
        sample = make_sample(args)
        sample.to_csv(args.out, index=False)
        print(f"wrote={args.out} rows={len(sample)} strata={sample[['field', 'cohort', 'length_bucket', 'detector_language']].drop_duplicates().shape[0]}")


if __name__ == "__main__":
    main()
