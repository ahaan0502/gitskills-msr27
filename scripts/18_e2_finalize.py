#!/usr/bin/env python3
"""E2 step 8: write the final range and limitation inventory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

from gitskills.config import OUT_DIR


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--classifications", type=Path, default=OUT_DIR / "e2_authorship_classifications.parquet")
    ap.add_argument("--out", type=Path, default=OUT_DIR / "e2_step8_final_range.csv")
    ap.add_argument("--inventory-out", type=Path, default=OUT_DIR / "e2_step8_unknown_inventory.csv")
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    classifications = str(args.classifications).replace("\\", "/")
    con = duckdb.connect()
    overall = con.execute(f"""
      SELECT COUNT(*)::BIGINT AS n_all,
             COUNT(*) FILTER (WHERE history_quality IS NOT NULL)::BIGINT AS n_history,
             COUNT(*) FILTER (WHERE history_quality IS NULL)::BIGINT AS n_unknown,
             COUNT(*) FILTER (WHERE history_quality IS NOT NULL AND creation_agent_explicit)::BIGINT AS creation_lower,
             COUNT(*) FILTER (WHERE history_quality IS NOT NULL AND maintenance_agent_explicit)::BIGINT AS maintenance_lower,
             COUNT(*) FILTER (WHERE history_quality IS NOT NULL AND maintenance_agent_any_event)::BIGINT AS maintenance_any_lower
      FROM read_parquet('{classifications}')
    """).df().iloc[0].to_dict()
    rows = []
    for signal, key in [("creation", "creation_lower"), ("maintenance_last_event", "maintenance_lower"), ("maintenance_any_event", "maintenance_any_lower")]:
        lower = int(overall[key])
        history = int(overall["n_history"])
        rows.extend([
            {"signal": signal, "bound": "explicit_lower_bound", "n": lower, "denominator_history": history, "share_history": lower / history, "classifier_status": "validated_screen"},
            {"signal": signal, "bound": "expanded_marker_estimate", "n": lower, "denominator_history": history, "share_history": lower / history, "classifier_status": "same_as_lower_bound_no_validated_expansion"},
            {"signal": signal, "bound": "upper_theoretical_ceiling", "n": history, "denominator_history": history, "share_history": 1.0, "classifier_status": "no_validated_upper_classifier"},
        ])
    pd.DataFrame(rows).to_csv(args.out, index=False)
    inventory = pd.DataFrame([
        {"case": "unknown_history", "n": int(overall["n_unknown"]), "share_all": int(overall["n_unknown"]) / int(overall["n_all"]), "interpretation": "No representative-level first/last history available; not human-authored evidence."},
        {"case": "history_available", "n": int(overall["n_history"]), "share_all": int(overall["n_history"]) / int(overall["n_all"]), "interpretation": "History-linked denominator used for lower-bound rates."},
        {"case": "agent_creation_lower_bound", "n": int(overall["creation_lower"]), "share_all": int(overall["creation_lower"]) / int(overall["n_all"]), "interpretation": "Explicit marker at first available event."},
        {"case": "agent_maintenance_last_lower_bound", "n": int(overall["maintenance_lower"]), "share_all": int(overall["maintenance_lower"]) / int(overall["n_all"]), "interpretation": "Explicit marker at last available event."},
        {"case": "agent_maintenance_any_lower_bound", "n": int(overall["maintenance_any_lower"]), "share_all": int(overall["maintenance_any_lower"]) / int(overall["n_all"]), "interpretation": "Explicit marker at any observed first/last event."},
    ])
    inventory.to_csv(args.inventory_out, index=False)
    metadata = {
        "n_all": int(overall["n_all"]),
        "n_history": int(overall["n_history"]),
        "n_unknown_history": int(overall["n_unknown"]),
        "upper_bound_note": "A validated upper-bound classifier was not established. The reported ceiling is theoretical only and is not an empirical estimate.",
        "limitations": [
            "Only first and last available events are observed; middle commits are not available.",
            "Human-committed agent work can be missed by explicit identity/message markers.",
            "Co-authorship markers without an identifiable agent claim remain ambiguous.",
            "History coverage is strongly associated with canonical location and dated cohorts.",
            "Repository concentration and repeated content change copy-inclusive results.",
        ],
    }
    (args.out.with_suffix(".json")).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"Wrote {args.out}")
    print(f"Wrote {args.inventory_out}")
    con.close()


if __name__ == "__main__":
    main()
