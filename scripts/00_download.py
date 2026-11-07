#!/usr/bin/env python3
"""Download the GitSkills Parquet mirror (selected tables) from Hugging Face.

Pins a dataset revision so the exact snapshot is recorded in data/raw/REVISION.txt.

Examples:
    # Core tables for E0-E2 (artifacts + repos), pinned to the current main revision
    python scripts/00_download.py

    # Also fetch the 7.3M-row siblings table (needed only for ClawHub/script flags)
    python scripts/00_download.py --tables artifacts repos artifact_siblings mining_runs

    # Re-download at a specific revision
    python scripts/00_download.py --revision <commit-hash>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gitskills.config import HF_REPO_ID, RAW_DIR  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--tables", nargs="+", default=["artifacts", "repos", "mining_runs"],
                    help="Table folders to fetch (default: artifacts repos mining_runs)")
    ap.add_argument("--revision", default=None, help="Dataset commit hash; default = current main")
    ap.add_argument("--out", type=Path, default=RAW_DIR)
    args = ap.parse_args()

    api = HfApi()
    revision = args.revision or api.dataset_info(HF_REPO_ID).sha
    print(f"Dataset {HF_REPO_ID} @ {revision}")

    args.out.mkdir(parents=True, exist_ok=True)
    patterns = [f"{t}/*" for t in args.tables]
    path = snapshot_download(
        repo_id=HF_REPO_ID,
        repo_type="dataset",
        revision=revision,
        allow_patterns=patterns + ["README.md"],
        local_dir=args.out,
    )
    (args.out / "REVISION.txt").write_text(f"{HF_REPO_ID}\n{revision}\ntables: {' '.join(args.tables)}\n")
    print(f"Done -> {path}")
    print("Next: python scripts/01_date_audit.py")


if __name__ == "__main__":
    main()
