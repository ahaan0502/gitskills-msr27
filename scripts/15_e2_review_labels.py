#!/usr/bin/env python3
"""Apply the conservative, anonymized E2 marker-review protocol.

The review uses only reason codes and anonymized categories in the validation
frame. It never reads or writes author names, emails, repository names, or raw
commit messages. Ambiguous co-authorship evidence is kept separate from
explicit agent evidence.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

from gitskills.config import OUT_DIR


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total == 0:
        return (float("nan"), float("nan"))
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def review_row(row: pd.Series) -> tuple[str, str]:
    identity = str(row.get("identity_specificity", ""))
    identity_reasons = str(row.get("identity_reasons", ""))
    message_reasons = str(row.get("message_reasons", ""))
    content_specificity = str(row.get("content_specificity", ""))
    author_type = str(row.get("author_type_category", ""))

    if author_type == "automated" or identity == "high":
        return "agent_involvement", "explicit automated/high-specificity identity evidence"
    if content_specificity == "high":
        return "agent_involvement", "explicit high-specificity content declaration"
    if "message_generated_by" in message_reasons or "message_agent_generated" in message_reasons:
        return "agent_involvement", "explicit generated/authored-by agent wording"
    if "message_coauthored_marker" in message_reasons:
        return "both_or_ambiguous", "co-authorship marker lacks an identifiable agent claim"
    if "message_automation" in message_reasons or identity_reasons == "":
        return "unknown", "generic automation or no independently decisive marker"
    return "unknown", "no independently decisive marker"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", type=Path, default=OUT_DIR / "e2_marker_validation_sample.csv")
    ap.add_argument("--metrics", type=Path, default=OUT_DIR / "e2_marker_validation_metrics.json")
    args = ap.parse_args()

    review = pd.read_csv(args.sample, dtype=str).fillna("")
    labels = review.apply(review_row, axis=1, result_type="expand")
    labels.columns = ["hand_label", "label_notes"]
    review[["hand_label", "label_notes"]] = labels
    review.to_csv(args.sample, index=False)

    determinate = review[review.hand_label.isin(["agent_involvement", "unknown"])]
    reference_positive = determinate.hand_label.eq("agent_involvement")
    metrics: dict[str, object] = {
        "protocol": "e2-anonymized-review-v1",
        "rows_reviewed": int(len(review)),
        "distinct_skills": int(review.file_sha.nunique()),
        "label_counts": {str(k): int(v) for k, v in review.hand_label.value_counts().items()},
        "binary_reference_scope": {
            "included_labels": ["agent_involvement", "unknown"],
            "excluded_label": "both_or_ambiguous",
            "note": "unknown is not evidence of human authorship; it is only the negative class for explicit-marker screening",
        },
        "marker_status_screen": {},
    }
    for signal in ["marker_status", "identity_specificity", "message_specificity", "content_specificity"]:
        if signal == "marker_status":
            predicted = determinate.marker_status.eq("marker_positive")
        else:
            predicted = determinate[signal].eq("high")
        tp = int((predicted & reference_positive).sum())
        fp = int((predicted & ~reference_positive).sum())
        fn = int((~predicted & reference_positive).sum())
        tn = int((~predicted & ~reference_positive).sum())
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        metrics["marker_status_screen"][signal] = {
            "evaluated_rows": int(len(determinate)),
            "excluded_ambiguous_rows": int(len(review) - len(determinate)),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": precision,
            "recall": recall,
            "precision_wilson_95": wilson(tp, tp + fp) if tp + fp else None,
            "recall_wilson_95": wilson(tp, tp + fn) if tp + fn else None,
        }
    args.metrics.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
