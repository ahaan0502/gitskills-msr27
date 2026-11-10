# GitSkills MSR 2027 Mining Challenge

CS 520 project repository for studying agent skill files mined from GitHub. The project uses the GitSkills dataset and follows the staged experiment plan in the project-plan PDF. The repository contains code and pushable documentation; the dataset and large generated artifacts are downloaded locally and ignored.

## Project goals

The project aims to build a reproducible empirical account of agent skills as software artifacts. The planned analysis examines how skills are authored and organized, how they vary across repositories and time, how often they are copied or templated, what languages they use, and how their wording, structure, semantics, and repository integration can be studied without conflating duplicate occurrences with distinct content.

The workflow is deliberately staged:

- E0 establishes the dataset snapshot, parser parity, date-coverage audit, distinct-content table, and reusable repository/content signals.
- E1 measures the natural-language distribution of descriptions, body prose, and paragraphs, including cohort, copy-frequency, and repository-flag sensitivities.
- E2 estimates explicit agent authorship and maintenance signals, separately for creation and later observed events, with history-coverage and repository-concentration sensitivities.
- E3-E6 are reserved for the later project-plan analyses of skill structure, reuse/convergence, phrasing or semantic patterns, and repository/integration effects. They have not been started.

## Research questions

The project plan is organized around these questions:

1. What kinds of agent skills are present in the GitSkills corpus, and how are they distributed across repositories and time?
2. How much of the observed corpus is distinct content versus copied, templated, catalog-like, or bulk-repository content?
3. What languages appear in skill descriptions and bodies, and do language shares change across the dated cohorts?
4. Do descriptions and body prose use the same language, and how often is skill content mixed-language?
5. How do skills vary in their structure, wording, and semantic content, and what forms of convergence or reuse can be measured?
6. What lower-bound share of distinct skills shows explicit agent involvement at creation or maintenance, and how sensitive is that result to incomplete history and repository concentration?
7. How are skills integrated into repositories and agent workflows, and what repository context is associated with their distribution or evolution?

The exact hypotheses, operational definitions, and scope limits for each experiment are documented in [docs/experiments](docs/experiments/). Measured results are documented in [docs/results](docs/results/).

## Dataset

- Dataset: GitSkills, a corpus of agent `SKILL.md` files mined from GitHub.
- Dataset mirror: `mvaccargiu/gitskills` on Hugging Face.
- Snapshot used here: revision `ebab17454a7c236f8f26b183567f1a126f42e3f8`.
- Local sample: a public SQLite sample used for fast development and parser validation.
- Full tables used in E0: `artifacts`, `repos`, and `mining_runs`; `artifact_siblings` was skipped for the full download at this stage.
- Primary E0/E1 unit: representative distinct contents (`dedup_primary = 1`), identified by `file_sha`.

The full snapshot contains about 1.88 million representative contents. Only representative rows have text and commit history. Date history is uneven across location classes, so dated cohort analyses are reported as a restricted population rather than as a complete census.

## Technology and libraries

The pipeline uses:

- Python 3.10 or newer.
- DuckDB for streaming Parquet queries, joins, aggregation, and memory-bounded processing.
- PyArrow for Parquet input/output and streaming batch operations.
- pandas for compact tabular summaries and validation tables.
- PyYAML for front-matter parsing.
- markdown-it-py for Markdown block parsing and paragraph reconstruction.
- lingua-language-detector 2.2.0 for multilingual detection in E1, using bundled models and 75 supported languages.
- huggingface_hub for downloading the pinned dataset mirror.
- pytest for parser and regression tests.
- Standard-library multiprocessing support for large representative-level parsing.

## Repository tools and pipeline

Important scripts include:

- `scripts/00_download.py` - downloads the pinned Hugging Face tables and records the revision.
- `scripts/00b_sample_to_parquet.py` - converts the SQLite sample into the mirror's per-table Parquet layout.
- `scripts/01_date_audit.py` - runs E0 Gate A date coverage and cohort audits.
- `scripts/02_build_skills.py` - parses one representative per distinct content hash into the derived skills table.
- `scripts/03_flags.py` - creates separate catalog, template, bulk-repository, and deterministic repository-rank signals.
- `scripts/04_validate_parser.py` - compares parser output against the dataset's own parsed fields.
- `scripts/05_e1_detect_language.py` - detects description, body, and paragraph languages.
- `scripts/06_e1_overall_language.py` - computes overall language shares.
- `scripts/07_e1_cohort_language.py` - computes cohort-by-language shares.
- `scripts/08_e1_description_body_agreement.py` - computes agreement and the description/body matrix.
- `scripts/09_e1_sensitivities.py` - computes copy-inclusive and E0-flag sensitivity analyses.
- `scripts/10_e1_validate_detector.py` - creates and scores the stratified reference-label validation sample.
- `scripts/11_e2_history_inventory.py` - inventories history availability and metadata fields for E2.
- `scripts/12_e2_build_evidence.py` - builds anonymized first/last authorship evidence.
- `scripts/13_e2_classify_outcomes.py` - creates representative-level explicit-marker outcomes.
- `scripts/14_e2_marker_validation_sample.py` and `scripts/15_e2_review_labels.py` - create and review the anonymized E2 validation sample.
- `scripts/16_e2_estimate_shares.py` - computes creation and maintenance shares by required strata.
- `scripts/17_e2_robustness.py` and `scripts/18_e2_finalize.py` - run E2 sensitivities and write the final range/limitation inventory.

The parser implementation is in `src/gitskills/parse.py`, configuration is in `src/gitskills/config.py`, and parser tests are in `tests/test_parse.py`.

## Documentation and experiment status

| Experiment | Status | Documentation |
| --- | --- | --- |
| E0 - data preparation | Complete | [methodology](docs/experiments/E0.md), [results](docs/results/E0-results.md) |
| E1 - natural-language distribution | Complete | [methodology](docs/experiments/E1.md), [results](docs/results/E1-results.md) |
| E2 - agent authorship and maintenance | Complete with empirical-upper-bound limitation | [methodology](docs/experiments/E2.md), [results](docs/results/E2-results.md) |
| E3 | Not started | [methodology](docs/experiments/E3.md), [results](docs/results/E3-results.md) |
| E4 | Not started | [methodology](docs/experiments/E4.md), [results](docs/results/E4-results.md) |
| E5 | Not started | [methodology](docs/experiments/E5.md), [results](docs/results/E5-results.md) |
| E6 | Not started | [methodology](docs/experiments/E6.md), [results](docs/results/E6-results.md) |

## Setup and reproducibility

```bash
python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
pytest
python scripts/00_download.py
python scripts/01_date_audit.py
```

The detailed E0 and E1 command sequences are recorded in their methodology documents. Generated files are written under `data/` and `outputs/` and are intentionally not part of the repository.

## Data, licensing, and anonymity safeguards

- Never commit anything under `data/` or `outputs/`, including Parquet, SQLite, ZIP, or other generated database files.
- The raw dataset's origin-repository licenses apply to downloaded content.
- Do not add author, contributor, repository-owner, or other identifying names to the double-anonymous repository or paper materials.
- Keep exact dataset revisions and methodological decisions in committed documentation so results remain reproducible without committing the data itself.
