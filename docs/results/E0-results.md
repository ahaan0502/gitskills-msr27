# E0 results - data preparation

Status: complete.

## Step 0 - scope and snapshot

E0 established the reproducible dataset snapshot, parser-parity checks, date audit, distinct-content table, and sampling flags. The full Hugging Face snapshot was pinned to revision `ebab17454a7c236f8f26b183567f1a126f42e3f8`. The downloaded tables were artifacts, repos, and mining_runs; artifact_siblings was intentionally skipped for the full download. All source data and large generated artifacts remain ignored.

## Step 1 - parser changes and tests

The parser was updated to match the dataset specification:

- `spec_valid` requires a YAML mapping with non-empty name and description.
- Closing front-matter fences accept three or more dashes.
- YAML failures attempt line-level recovery of name and description and set `fm_recovered=true` while retaining `frontmatter_valid=false`.
- Body length counting preserves the dataset's CRLF convention.

Parser tests cover valid/invalid front matter, the widened closing fence, YAML recovery, and body parsing. The final test suite passed all 16 tests.

## Step 2 - sample conversion and parser validation

The public SQLite sample was downloaded into ignored data storage and converted to per-table Parquet. The converted sample contained:

| Table | Rows |
| --- | ---: |
| artifacts | 29,786 |
| repos | 11,841 |
| artifact_siblings | 47,829 |
| mining_runs | 7 |

The sample had 13,000 representative distinct contents. Agreement against the dataset fields was:

| Check | Agreement |
| --- | ---: |
| spec_valid | 99.600% |
| name | 99.638% |
| description | 99.615% |
| body_chars | 99.062% |

There were 321 YAML-recovered representatives and 125 disagreement rows. The body-count result is below the original 99.5% target; this limitation is retained rather than hidden. The remaining examples include dataset-accepted YAML forms that PyYAML rejects and nonstandard closing fences.

## Step 3 - sample Gate A date audit

The sample reproduced the expected date-audit pattern:

- 3,010 of 13,000 representatives had usable dates.
- Dated cohorts ran from October 2025 through July 2026.
- History coverage was 99.6% for canonical locations, 11.0% for skills-directory locations, and 11.6% for other locations.
- 38.1% of dated skills were first committed within one day of repository creation.

The dated subset is therefore strongly biased toward canonical locations and is not representative of all detected skills.

## Step 4 - full download and Gate A

The full pinned snapshot contained 1,877,981 representatives. Gate A found:

| Date category | Representatives |
| --- | ---: |
| In-window, October 2025 through July 2026 | 457,985 |
| No usable date | 1,419,844 |
| Before the format window | 152 |

Among the 458,062 records with both repository and skill dates, 36.4% were first committed within one day of repository creation. History coverage was 99.6% for canonical locations, 11.7% for skills-directory locations, and 11.4% for other locations. Filename auditing found 1,842,600 exact `SKILL.md` occurrences and 35,381 non-exact filenames.

The ten dated cohorts are October 2025 through July 2026, with July treated as partial. Date availability remains a major selection limitation for any cohort analysis.

Monthly Gate A cohorts were:

| Cohort | Distinct contents | Repositories |
| --- | ---: | ---: |
| 2025-10 | 1,265 | 435 |
| 2025-11 | 3,578 | 1,039 |
| 2025-12 | 6,615 | 2,024 |
| 2026-01 | 20,918 | 6,673 |
| 2026-02 | 49,234 | 12,298 |
| 2026-03 | 78,540 | 21,486 |
| 2026-04 | 84,062 | 25,020 |
| 2026-05 | 86,254 | 24,379 |
| 2026-06 | 85,855 | 26,031 |
| 2026-07 | 41,664 | 14,899 |

## Step 5 - distinct-content skill table

The parser output `outputs/skills.parquet` contains 1,877,981 representative rows and 22 columns. Only representatives (`dedup_primary=1`) received text parsing and history-linked fields. A first multiprocessing implementation caused an out-of-memory error because of an unnecessary global sort; streaming without that sort completed successfully. The restricted managed environment required a one-worker fallback, while the multiprocessing option remains available in less restricted environments.

## Step 6 - signal flags and per-repository rank

The flags output contains 1,877,981 rows and 1,877,981 distinct file hashes. Signals were retained separately:

| Signal | Threshold/rule | Positive rows |
| --- | --- | ---: |
| catalog_flag | catalog/path marker heuristic | 118,054 |
| template_flag | same normalized content in at least 5 repositories | 188,072 |
| bulk_repo_flag | repository contains at least 50 skills | 911,456 |

The deterministic `repo_rank` was also generated for later per-repository capping. Integrity checks confirmed row count, distinct hashes, rank bounds, and flag columns.

## Reproducibility commands

```text
python scripts/00b_sample_to_parquet.py data/sample/agent_skills_sample.db --out data/sample_parquet
python scripts/04_validate_parser.py --raw data/sample_parquet --out outputs/validation_sample
python scripts/01_date_audit.py --raw data/sample_parquet --out outputs/date_audit_sample
python scripts/00_download.py
python scripts/01_date_audit.py --raw data/raw --out outputs/date_audit_full
python scripts/02_build_skills.py --raw data/raw --out outputs/skills.parquet --workers 1 --batch-size 2000
python scripts/03_flags.py --raw data/raw --skills outputs/skills.parquet --out outputs/skills_flags.parquet --template-min-repos 5 --bulk-repo-min-skills 50
```

## E0 output inventory

The detailed numeric CSVs and Parquet tables remain in ignored data/output locations. The committed methodology and execution record are in [experiments/E0.md](../experiments/E0.md). No data, Parquet, SQLite, ZIP, or generated database file is intended for Git.
