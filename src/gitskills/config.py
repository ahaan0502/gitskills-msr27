"""Central constants. Paths are relative to the repo root unless overridden by env vars."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("GITSKILLS_DATA", REPO_ROOT / "data"))
OUT_DIR = Path(os.environ.get("GITSKILLS_OUT", REPO_ROOT / "outputs"))

HF_REPO_ID = "mvaccargiu/gitskills"
RAW_DIR = DATA_DIR / "raw"          # downloaded Parquet mirror (untouched)
SAMPLE_DIR = DATA_DIR / "sample"    # GitHub sample (SQLite)

# Format launched Oct 2025; collection ran July 2026 (July is a partial cohort).
FORMAT_START = "2025-10-01"
COLLECTION_END = "2026-07-31"
