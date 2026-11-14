# E3-r01-primary

Status: complete; Steps 1-8 complete.

## Run identity

- Experiment: E3
- Purpose: Primary structural convergence analysis
- Parent run: —
- Triggering experiment: —
- Data revision: GitSkills pinned revision documented in the project README
- Methodology: [E3 experiment plan](../../experiments/E3.md)
- Output directory: `outputs/runs/E3-r01-primary/`

This record will be expanded as `E3-r01-primary` proceeds. It contains the frozen population, structural-feature version, parameters, validation, results, and limitations for this run only.

## Step 1 - input inventory and population freeze

Executed with:

```text
python scripts/19_e3_input_inventory.py
```

The ignored inventory is under `outputs/runs/E3-r01-primary/step1_input_inventory/` and contains `schema.json`, `metrics.csv`, `cohort_counts.csv`, and `summary.json`. The inventory contains field names and aggregate counts only; it does not export raw skill text or identifying metadata.

### Frozen input counts

| Measure | Count | Context |
| --- | ---: | --- |
| Parsed skills rows | 1,877,981 | One row per representative `file_sha` |
| Distinct `file_sha` values | 1,877,981 | No duplicate representatives |
| Artifact occurrences | 3,797,117 | Full artifact table |
| E0-window dated representatives | 457,985 | October 2025 through July 2026; reconciles with E0 |
| `spec_valid` parsed rows | 1,631,415 | Parser-derived structural-validity field |
| `frontmatter_valid` parsed rows | 1,666,180 | Parser field |
| `fm_recovered` rows | 44,706 | YAML-error recovery marker |
| `parse_error` rows | 44,838 | Non-empty parse-error field |

The E0-valid cohort counts are: 1,265 (2025-10), 3,578 (2025-11), 6,615 (2025-12), 20,918 (2026-01), 49,234 (2026-02), 78,540 (2026-03), 84,062 (2026-04), 86,254 (2026-05), 85,855 (2026-06), and 41,664 (2026-07). The `other_or_undated` group contains 1,419,996 representatives, with only 152 having a first-commit date outside the E0 window; it is retained for overall counts but excluded from dated cohort comparisons.

### E0 flag and rank reconciliation

The E0 flags table contains 1,877,981 rows and 1,877,981 distinct `file_sha` values. `repo_rank` has no nulls, with minimum 1 and maximum 30,308. Flag counts are 118,054 catalog, 188,072 template, and 911,456 bulk-repository representatives. These fields are available for later E3 sensitivity analyses.

Step 1 is complete. The population and input schema are frozen for `E3-r01-primary`.

## Step 2 - structural extractor checkpoint

The extractor is [scripts/20_e3_build_structure.py](../../../scripts/20_e3_build_structure.py), using [src/gitskills/structure.py](../../../src/gitskills/structure.py) version `e3-structure-v1`. Tests for the extractor were added and the suite passed with 26 tests. The execution uses one worker because a four-worker launch was blocked by a Windows multiprocessing permission error. The restarted run writes durable batch parts, a progress JSON, a run log, and a completion marker; it publishes the final Parquet only after row-count and distinct-key checks pass.

An earlier incomplete checkpoint contained 805,000 rows and was intentionally removed at the user's request. Step 2 was rerun from the full 1,877,981-representative population using the durable-output method. The completed output contains 1,877,981 rows and 1,877,981 distinct `file_sha` values across 376 batch parts; the completion marker is present. Step 3 has not started.

The first complete output had body/heading-count mismatches caused by structural front-matter splitting not exactly matching the canonical E0 parser. The extractor was corrected to reuse the parser's normalization and split rules, and the output was regenerated successfully with 1,877,981 rows, 1,877,981 distinct `file_sha` values, 376 batches, and a completion marker. Step 3 was then rerun against this corrected output and passed.

## Step 3 - structural extraction validation

The validator is [scripts/21_e3_validate_structure.py](../../../scripts/21_e3_validate_structure.py). It compares the structural output with the E0 skills table, writes an anonymized 200-row deterministic sample, records the feature schema and status counts, and does not write raw skill text. The first launch used the system Python and failed before execution because DuckDB was unavailable; the project `.venv` launch completed successfully.

All 1,877,981 rows passed: feature row count, distinct `file_sha`, body character/word/line counts, heading counts, heading-array lengths, normalized front-matter key counts, structure status, and `e3-structure-v1` version. Status counts are 1,827,003 `ok`, 44,838 `parser_error_present`, 6,138 `symlink_like`, and 2 `empty`. The validation artifacts are under `outputs/runs/E3-r01-primary/step3_structure_validation/`.

Step 3 was rerun against the final metadata-enriched output using [scripts/21_e3_validate_structure.py](../../../scripts/21_e3_validate_structure.py). All row, distinct-key, parser-feature, status, structure-version, cohort, location, flag, and `repo_rank` checks passed for 1,877,981 rows. The deterministic anonymized validation sample and metrics are under `outputs/runs/E3-r01-primary/step3_structure_validation/`.

## Step 4 - overall structural distributions

The aggregate script is [scripts/22_e3_overall_structure.py](../../../scripts/22_e3_overall_structure.py). It wrote size, feature-prevalence, section-frequency, front-matter-key, block-frequency, template-frequency, and template-concentration tables under `outputs/runs/E3-r01-primary/step4_overall_structure/`.

Across 1,877,981 representatives, mean body size is 6,955 characters, median 4,598; mean body words 931.6, median 621; mean headings 13.71, median 11; and median maximum heading depth 3. Feature prevalence includes headings in 97.295% of skills, bullet lists in 91.611%, ordered lists in 66.110%, tables in 41.350%, code blocks in 67.156%, inline code in 79.909%, block quotes in 16.641%, and thematic breaks in 20.865%.

The structural representation yields 1,396,458 unique template signatures with entropy 19.169 bits. The most common template covers 3.187% of skills; the top 100 cover 7.424%; and the top 1,000 cover 11.007%. The most frequent normalized sections by skill coverage are `when to use` (238,194), `overview` (226,496), `workflow` (190,919), `best practices` (159,842), and `output format` (155,579). These are descriptive overall distributions, not cohort convergence claims.

## Step 5 - cohort structural trends

The cohort script is [scripts/23_e3_cohort_structure.py](../../../scripts/23_e3_cohort_structure.py). It analyzes the ten E0-valid cohorts from 2025-10 through 2026-07 and excludes `other_or_undated` from cohort comparisons. Outputs are under `outputs/runs/E3-r01-primary/step5_cohort_structure/` and include cohort size summaries, feature prevalence with Wilson 95% intervals, template frequencies, concentration, and entropy.

Median body size declines from 7,935 characters in 2025-10 to 5,141 in 2026-07, with a non-monotonic path; median headings decline from 21 to 9. Heading prevalence declines from 98.972% to 96.921%, multiple-heading prevalence from 98.340% to 93.997%, and ordered-list prevalence from 78.024% to 66.398%. Table prevalence rises from 19.526% to 40.555%, while code-block prevalence declines from 85.059% to 66.441%. Inline-code prevalence rises from 82.530% to 91.057%.

Template entropy rises from 10.190 bits in 2025-10 to 14.945 bits in 2026-07, but the 2026-02 cohort has an unusually high top-template share of 14.220%, compared with 0.632% in 2025-10 and 0.278% in 2026-07. This concentration spike is retained for Step 7 sensitivity analysis and is not interpreted as a general convergence result. July is partial, and cohort sizes differ substantially.

Step 5 is complete. The Step 6 section below records the robustness analysis.

## Step 6 - robustness to reuse and repository signals

The robustness script is [scripts/24_e3_robustness.py](../../../scripts/24_e3_robustness.py). It writes aggregate-only outputs under `outputs/runs/E3-r01-primary/step6_robustness/`: overall sensitivity summaries, cohort sensitivity summaries, location strata, and a run summary. It does not export repository names, author fields, raw skill text, or representative identifiers.

The primary distinct population has 1,877,981 representatives. Copy-inclusive analysis has 3,797,117 artifact occurrences and 1,877,981 distinct contents. The combined catalog/template/bulk exclusion retains 906,970 representatives, and the per-repository cap of 50 retains 1,198,436. The primary cohort pattern persists after both controls: median body size changes from 7,935 to 5,141 characters and median headings from 21 to 9; the combined-exclusion sensitivity changes from 7,539 to 4,953 characters and 20 to 8 headings; the repository-cap sensitivity changes from 7,834 to 5,158 characters and 21 to 8 headings.

Copy-inclusive weighting changes the levels but preserves the direction: median body size changes from 9,136 to 6,434 characters and median headings from 23 to 11. The February 2026 top-template concentration remains anomalous in the primary population at 14.247%, while the July value is 0.281%. Under combined exclusions and the repository cap, July top-template shares are 0.145% and 0.142%, respectively. This supports treating the February spike as a cohort-specific sensitivity issue, not evidence of general convergence. Location strata show level differences, including code-block prevalence, and are retained descriptively.

Step 6 is complete. The Step 7 section below records the concentration and similarity analysis.

## Step 7 - concentration and structural similarity

The analysis script is [scripts/25_e3_concentration_similarity.py](../../../scripts/25_e3_concentration_similarity.py). Full-population cohort concentration outputs are under `outputs/runs/E3-r01-primary/step7_concentration_similarity/`. These report top-template coverage, Shannon entropy, and effective template count (`2**entropy`). Cross-cohort similarity uses deterministic equal samples of 25 representatives per cohort, selected by the lowest MD5 values of the anonymized `file_sha` join key; identifiers are discarded before output. The 10 cohorts produce 45 pair comparisons with 625 representative pairs each.

Effective template count rises from 1,168 in 2025-10 to 31,534 in 2026-07. February 2026 remains anomalous: its effective template count is 10,590 and its top-template share is 14.220%, versus 0.278% in July. Across all 45 sampled cohort pairs, mean feature-set Jaccard similarity is 0.581 and mean block-sequence similarity is 0.328. The earliest/latest comparison is 0.594 feature Jaccard and 0.316 block-sequence ratio. Exact template matches are nearly absent in the sample (0.014% overall), so the shared coarse feature structure does not imply identical templates.

The pairwise results are descriptive sample statistics, not population-wide estimates. The sample is equal-sized and deterministic to prevent cohort size from driving comparisons; concentration and entropy use all representatives in each dated cohort. Step 7 is complete.

## Step 8 - structural convergence interpretation and limitations

E3 does not support a simple claim that later skills converge on one increasingly dominant structural format. Later cohorts are generally shorter and contain fewer headings, but template entropy and effective template counts generally increase, and exact template matches are rare. The evidence is more consistent with recurring structural features plus a broadening long tail of templates, with cohort-specific concentration anomalies rather than monotonic convergence.

Limitations include E0 date coverage bias, partial July coverage, unequal cohort sizes, copied/template/bulk-repository reuse, and Markdown/parser ambiguities. Parser-error and symlink-like records remain explicit statuses. The Step 6 sensitivities show how reuse and repository weighting affect levels, and Step 7 similarity is a deterministic 25-per-cohort sample rather than a population-wide estimate. Structural similarity does not establish shared authorship, common provenance, semantic equivalence, or causal influence.

All E3 acceptance criteria are satisfied: `e3-structure-v1` is tested and validated; denominators reconcile to E0; structural distributions, cohort trends, sensitivities, concentration, entropy, and sampled similarity are reported; limitations are explicit; and no raw text or identifying metadata is included in committed documentation. E6 reruns must preserve the feature version and stable anonymized join key while receiving new run IDs.

E3-r01-primary is complete. E4 has not started.
