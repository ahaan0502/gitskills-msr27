# gitskills-msr27

Analysis pipeline for the MSR 2027 Mining Challenge, GitSkills dataset
(Destefanis et al., [arXiv:2608.10906](https://arxiv.org/abs/2608.10906)).

**This repo contains code only.** The dataset (13+ GB) is downloaded separately and is git-ignored.
Cite the dataset version you use (Zenodo DOI 10.5281/zenodo.21875637); `scripts/00_download.py`
records the exact Hugging Face revision in `data/raw/REVISION.txt`.

## Layout

```
gitskills-msr27/
├── README.md
├── pyproject.toml          # dependencies (pip install -e ".[dev]")
├── .gitignore              # data/, *.parquet, *.sqlite are never committed
├── data/                   # (git-ignored) raw Parquet + GitHub sample
│   ├── raw/                #   Hugging Face mirror, one folder per table
│   └── sample/             #   277 MB SQLite sample for fast development
├── outputs/                # (git-ignored for big files) derived tables and reports
├── scripts/
│   ├── 00_download.py      # fetch tables from Hugging Face, pin revision
│   └── 01_date_audit.py    # E0 Gate A: what dates exist, for how much data
├── src/gitskills/
│   ├── config.py           # paths and constants
│   └── parse.py            # SKILL.md -> record (front matter, headings, code, prose)
├── tests/
│   └── test_parse.py       # golden/edge-case tests for the parser
└── docs/                   # plan, decisions, E0 report (add as you go)
```

Planned next (not yet written): `02_build_skills.py` (parse all distinct contents into
`skills.parquet`), `03_flags.py` (catalog/template/bulk-repo flags), `04_validate.py`
(agreement with dataset's own parsed fields), then E1 onward.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                                                # parser tests should all pass
python scripts/00_download.py                         # artifacts + repos + mining_runs
python scripts/01_date_audit.py                       # writes outputs/date_audit/
```

## Notes

- Representative rows (`dedup_primary = 1`) are the only ones with text and commit history;
  all date analyses use them. See `outputs/date_audit/` for coverage.
- Do not commit dataset content. Origin-repo licenses apply to the `content` field.
- Submission is double-anonymous: do not put names in a public repo before review
  (use https://anonymous.4open.science/ if you share it).
