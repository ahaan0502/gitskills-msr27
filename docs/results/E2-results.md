# E2 results - agent authorship and maintenance

Status: E2 execution complete; the empirical upper-bound classifier is unavailable and is reported as a theoretical ceiling only.

## Step 1 - history and metadata inventory

The inventory used the full raw artifacts and repositories Parquet tables and representatives only (`dedup_primary = 1`). It wrote aggregate availability metrics and a schema inventory to the ignored `outputs/e2_history_inventory/` directory. No author names, emails, commit messages, or other identity values were exported.

### Population and history linkage

| Quantity | Count | Share/interpretation |
| --- | ---: | --- |
| Artifact occurrences | 3,797,117 | Full artifact table |
| Representative contents | 1,877,981 | Primary E2 population |
| Representatives with history fetched true | 458,137 | 24.395% of representatives |
| Representatives with first commit date | 458,137 | Same history-available subset |
| Representatives with last commit date | 458,137 | Same history-available subset |
| Distinct representative repositories linked to repository metadata | 242,732 | Joined by repository full-name key |
| Repository metadata rows | 282,200 | Full repos table |

The 458,137 history records are the usable event-history denominator currently available for E2. This is distinct from the E0 dated count: E0's 457,985 in-window records apply the October 2025 through July 2026 date restriction, while E2 Step 1 inventories all fetched histories before applying cohort restrictions.

### Available artifact history fields

The artifacts schema contains:

- First and last commit timestamps: `first_commit_at`, `last_commit_at`.
- First and last commit author identifiers: `first_commit_author`, `last_commit_author`.
- First and last commit author types: `first_commit_author_type`, `last_commit_author_type`.
- First and last commit messages: `first_commit_message`, `last_commit_message`.
- Commit count: `commit_count`.
- History linkage and quality fields: `history_fetched`, `content_fetched`, `composition_fetched`, `composition_truncated`, and `content_sha_ok`.

All five event-level history fields required for the initial E2 design—first/last date, first/last author, first/last message, and commit count—are populated for 458,137 representatives. The commit-count distribution has minimum 1, mean 2.228, median 1, and maximum 708.

### First/last author continuity

First and last commit author identifiers are equal for 435,974 of the 458,137 history records, or 95.162%. This is an aggregate comparison only; identifiers were not written to the repository. The result means that a first-versus-last author comparison will have limited discriminating power for many one-commit or single-author histories, so E2 must report one-commit histories separately.

### Author-type availability

Author-type values are metadata categories, not author identities. The observed representative counts were:

| Event | Null | Empty | User | Bot | Organization | Mannequin | ProgrammaticAccessBot |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| First commit | 1,419,844 | 62,750 | 390,600 | 4,630 | 153 | 3 | 1 |
| Last commit | 1,419,844 | 62,797 | 389,262 | 5,918 | 156 | 3 | 1 |

The non-null/filled type categories are available only where history was fetched. The null category is dominated by the no-history population and must not be interpreted as human authorship.

### Repository metadata availability

The repository table contains `full_name`, `owner`, `stars`, `forks`, `is_fork`, `language`, `license`, `description`, `created_at`, `pushed_at`, and `metadata_fetched`. Non-null counts were:

| Repository field | Non-null rows |
| --- | ---: |
| full_name | 282,200 |
| created_at | 281,685 |
| language | 281,685 |
| description | 169,059 |

Repository metadata is therefore sufficient for repository-level linkage and stratification, but description and language fields are incomplete and should remain explicit missingness categories.

## Step 1 command and output

```text
python scripts/11_e2_history_inventory.py
```

The reproducible inventory script is [scripts/11_e2_history_inventory.py](../../scripts/11_e2_history_inventory.py). Its ignored outputs are `outputs/e2_history_inventory/schema.json` and `outputs/e2_history_inventory/availability.csv`.

## Step 1 decisions for later E2 work

- Use 458,137 fetched-history representatives as the initial history-available denominator.
- Apply the E0 date window only for cohort-specific estimates, not for the initial schema inventory.
- Separate one-commit histories from multi-commit histories before interpreting creation versus maintenance.
- Treat null and empty author types as unknown, never as human-authored.
- Keep all identity values transient and aggregate only into double-anonymous counts.

Step 1 was complete at this point in the execution sequence; marker dictionaries, classifications, hand labels, and prevalence estimates were produced in later steps.

## Step 2 - versioned marker specification and normalization

Step 2 created `src/gitskills/e2_markers.py` with marker specification version `e2-marker-spec-v1`. The module returns reason codes and specificity levels only; it does not persist author names, emails, commit messages, or other raw identity values.

The marker families are:

| Family | Evidence represented | Specificity handling |
| --- | --- | --- |
| identity | automated author-type categories and generic identity tokens | high/medium positive evidence; user, organization, and mannequin types are non-positive low-specificity context |
| message | generated-by, agent/model-generated, automation, and co-authorship declarations | explicit declarations are high; broad automation terms are medium |
| content | explicit generated/created/written-by-agent declarations in skill content | explicit agent declarations are high; generic automatic-generation wording is medium |
| workflow | agent/assistant/model/automation terms near generate/create/write/maintain actions | medium candidate evidence, kept separate from commit evidence |

Normalization applies Unicode NFKC, case folding, removal of zero-width/BOM characters, and whitespace collapsing. Every match returns a family, reason code, and specificity tier. Author-type matching recognizes only dataset-level categories such as Bot and ProgrammaticAccessBot as automated markers; ordinary User, Organization, and Mannequin categories are not treated as proof of human authorship. Workflow/repository rules were specified for future use, but the executed E2 evidence table operationalized identity, message, and content signals only; no repository/workflow marker was used in the reported shares.

Added tests cover versioning, normalization, family separation, high-specificity declarations, automated author-type categories, and non-positive human-like categories. The full test suite passes with 23 tests.

Step 2 was complete at this point in the execution sequence; event-level evidence and later validation artifacts were created in Steps 3-5.

## Step 3 - anonymized event-level evidence

The evidence builder is [scripts/12_e2_build_evidence.py](../../scripts/12_e2_build_evidence.py). It reads only representatives with fetched history and populated first/last commit dates, processes source values transiently, applies the Step 2 marker families, and writes reason codes and specificity tiers without writing author names, emails, or commit messages.

The ignored output `outputs/e2_authorship_evidence.parquet` contains 612,377 rows and 15 columns:

- 303,897 `single_commit_or_same_endpoints` rows represented as `first_and_last` events.
- 154,240 `first` rows and 154,240 `last` rows represented as `first_last_only_no_middle_events` histories.
- 458,137 distinct representative hashes, matching the Step 1 history-available denominator.

The output records anonymized file hash, event position, event date, commit count, history quality, author-type category, and separate identity, message, and content marker fields with reason codes and specificity. It intentionally does not claim to observe middle commits because the available raw schema exposes first/last event fields rather than complete event histories.

Aggregate marker-field counts in the evidence table were 534,477 identity-marker rows, 249,022 message-marker rows, and 896 content-marker rows. These are evidence-field counts, not authorship estimates; no prevalence interpretation is made before validation and classification. Author-type categories were 526,931 non-automated-category rows, 7,546 automated rows, and 77,900 unknown rows.

Step 3 was complete at this point in the execution sequence; representative-level outcomes and prevalence estimates were created in Steps 4-8.

## Step 4 - representative-level outcome definitions

The outcome builder is [scripts/13_e2_classify_outcomes.py](../../scripts/13_e2_classify_outcomes.py). It joins the anonymized event evidence to all 1,877,981 representative skills and creates one classification row per `file_sha`. Explicit-marker lower-bound positives require an automated author-type category or a high-specificity identity, message, or content marker at the relevant first/last event.

The output `outputs/e2_authorship_classifications.parquet` contains one row per representative with:

- first/last event date, commit count, and history quality;
- `creation_agent_explicit`;
- `maintenance_agent_explicit`;
- `maintenance_agent_any_event`;
- `authorship_unknown`;
- `authorship_class_lower`;
- reserved nullable human-like, expanded, and upper-bound classification columns;
- `classification_status`.

The provisional lower-bound class counts are:

| Lower-bound class | Representatives |
| --- | ---: |
| agent_created_and_maintained | 134,405 |
| agent_created_only | 14,580 |
| agent_maintained_only | 19,013 |
| no_explicit_agent_evidence | 290,139 |
| unknown_history | 1,419,844 |

These are outcome-column counts, not final authorship estimates. At the Step 4 classification stage, expanded and upper-bound columns remained null pending marker validation and classifier decisions. Human-like classes also remain undefined because absence of an agent marker is not evidence of human authorship. Step 4 was complete; the Step 5 sample was then reviewed using the protocol below.

## Step 5 - marker validation sample

The sampler is [scripts/14_e2_marker_validation_sample.py](../../scripts/14_e2_marker_validation_sample.py). It creates an ignored, anonymized review CSV without author names, emails, or raw commit messages. Sampling is stratified by event position, E0 date cohort, E1 body-language group, body-text length bucket, and marker status; location class and E0 flags are retained as metadata rather than used as additional partition dimensions.

The corrected sample contains 728 rows covering 698 distinct skills:

| Marker status | Rows |
| --- | ---: |
| marker_positive | 347 |
| marker_negative | 381 |

The review was executed by [scripts/15_e2_review_labels.py](../../scripts/15_e2_review_labels.py) using only the anonymized reason codes and categories in the CSV. The protocol labeled explicit automated/high-specificity identity or explicit generated/authored-by agent evidence as `agent_involvement`; co-authorship evidence without an identifiable agent claim as `both_or_ambiguous`; and generic automation or no decisive marker as `unknown`. It did not treat absence of an agent marker as human authorship.

The resulting labels were:

| Review label | Rows |
| --- | ---: |
| agent_involvement | 6 |
| both_or_ambiguous | 341 |
| unknown | 381 |

For strict binary screening, the 341 ambiguous rows were excluded. On the remaining 387 rows, the combined `marker_status` screen had 6 true positives, 0 false positives, 0 false negatives, and 381 true negatives: precision 1.000 (Wilson 95% CI 0.610-1.000) and recall 1.000 (Wilson 95% CI 0.610-1.000). Identity and message high-specificity screens each had 4 true positives, 0 false positives, 2 false negatives, and 381 true negatives; precision was 1.000 (0.510-1.000) and recall 0.667 (0.300-0.903). No content marker appeared in the sample. These intervals are wide because only six cases received a decisive positive label.

The metrics are screening validation, not a prevalence estimate. The source frame contains reason codes rather than raw author/message text, so co-authorship markers cannot be independently attributed to an agent and remain ambiguous. Step 5 is complete; the subsequent Step 6 estimates use the validated explicit screen.

## Step 6 - creation and maintenance shares

The estimator is [scripts/16_e2_estimate_shares.py](../../scripts/16_e2_estimate_shares.py). It joins the representative-level lower-bound classifications to E0 cohort/location fields, E1 body-language fields, and the catalog/template/bulk flags. It writes the full stratified table to the ignored `outputs/e2_step6_summary.csv` and the overall row to `outputs/e2_step6_overall.csv`. Rates are reported both over all representatives and over the history-available denominator; Wilson 95% intervals apply to history-conditioned rates.

The distinct-content primary population contains 1,877,981 representatives. History is available for 458,137 (24.395%), leaving 1,419,844 (75.605%) in `unknown_history`. Among the history-available representatives:

| Lower-bound signal | Positive | Share | Wilson 95% CI |
| --- | ---: | ---: | --- |
| Agent at creation | 148,985 | 32.520% | 32.384%-32.656% |
| Agent at last available event | 153,418 | 33.487% | 33.351%-33.624% |
| Agent at any observed event | 167,998 | 36.670% | 36.530%-36.810% |

Using all representatives as the denominator, the corresponding shares are 7.933%, 8.169%, and 8.946%. These are explicit-marker lower-bound shares, not estimates of all agent work: human-committed agent work and unknown histories remain outside the positive class.

The cohort-conditioned creation shares range from 29.577% in 2026-02 to 40.939% in 2026-07; last-event maintenance shares range from 29.504% in 2026-02 to 41.369% in 2026-07. The dated cohorts have complete history coverage by construction of the date-linked subset, while `other_or_undated` contains 1,419,996 representatives but only 152 with usable history, so it must not be interpreted as a comparable cohort.

Location-conditioned creation/last-event shares are 38.458%/39.747% for canonical, 26.665%/26.844% for other, and 22.272%/22.936% for skills-dir. Catalog-flagged representatives are lower than non-catalog representatives (20.950%/21.625% versus 32.891%/33.868%); template-flagged representatives are lower (23.865%/26.454% versus 33.671%/34.423%); and bulk-repository representatives are lower (27.695%/29.080% versus 35.140%/35.881%). These comparisons are descriptive and inherit the history-coverage bias documented in E0.

For history quality, `single_commit_or_same_endpoints` has a 30.345% creation share and 30.345% last-event maintenance share, while `first_last_only_no_middle_events` has 36.805% and 39.679%. The any-observed-event shares are 30.345% and 49.128%, respectively. The complete language-by-language results, including all non-English languages and denominators, are in the ignored Step 6 summary CSV.

Step 6 is complete; the subsequent Step 7 section reports robustness and concentration checks.

## Step 7 - robustness and concentration checks

The sensitivity estimator is [scripts/17_e2_robustness.py](../../scripts/17_e2_robustness.py). It writes the complete sensitivity table, including Wilson intervals, to the ignored `outputs/e2_step7_robustness.csv`. The primary distinct-content estimate remains the reference; copy-inclusive and repository-capped results are sensitivities only.

The history-conditioned shares from the main sensitivity runs are:

| Sensitivity | History n | Creation | Last event | Any observed event |
| --- | ---: | ---: | ---: | ---: |
| Distinct, explicit lower bound | 458,137 | 32.520% | 33.487% | 36.670% |
| Expanded marker, current validated rules | 458,137 | 32.520% | 33.487% | 36.670% |
| Dated history only | 457,985 | 32.530% | 33.498% | 36.681% |
| Exclude catalog | 443,908 | 32.891% | 33.868% | 37.106% |
| Exclude template | 404,360 | 33.671% | 34.423% | 37.817% |
| Exclude bulk repository | 296,896 | 35.140% | 35.881% | 39.272% |
| Exclude all three signals | 274,867 | 35.841% | 36.616% | 40.118% |
| Repository cap of 50 | 353,435 | 34.480% | 35.346% | 38.720% |
| Copy-inclusive occurrences | 1,568,408 | 29.802% | 30.034% | 31.580% |

The copy-inclusive population contains 3,797,117 artifact occurrences and has a different history denominator because occurrences inherit history from their representative content. It is therefore not interchangeable with the distinct-content denominator. Excluding catalog, template, and bulk signals raises the shares, while copy-inclusive weighting lowers them, indicating sensitivity to repository composition and repeated content. The repository cap also raises the rates modestly, consistent with concentration among high-volume repositories.

The first/last/any-event comparisons are present in every row of the ignored CSV. No separate expanded-marker rule is reported yet: Step 5 did not validate lower-specificity markers sufficiently to justify expansion, so the current expanded sensitivity is deliberately identical to the explicit lower bound. Step 7 is complete; the Step 8 final report follows below.

## Step 8 - final range and limitations

The finalizer is [scripts/18_e2_finalize.py](../../scripts/18_e2_finalize.py). It writes the final range to the ignored `outputs/e2_step8_final_range.csv`, the excluded/unknown inventory to `outputs/e2_step8_unknown_inventory.csv`, and machine-readable limitation metadata beside the range output.

The final history-conditioned range is:

| Signal | Explicit lower bound | Expanded estimate | Upper-bound status |
| --- | ---: | ---: | --- |
| Creation | 32.520% (148,985/458,137) | 32.520% | Theoretical ceiling 100.000%; no validated empirical classifier |
| Last available event | 33.487% (153,418/458,137) | 33.487% | Theoretical ceiling 100.000%; no validated empirical classifier |
| Any observed event | 36.670% (167,998/458,137) | 36.670% | Theoretical ceiling 100.000%; no validated empirical classifier |

The expanded estimate is intentionally equal to the lower bound: Step 5 did not validate a lower-specificity marker rule suitable for expansion. The 100% upper value is only the logical ceiling among history-available representatives, not a claim that all skills were agent-authored or maintained. A useful empirical upper-bound classifier would require additional independently labeled positive and negative examples, especially for ambiguous co-authorship and workflow evidence.

The unknown/excluded inventory is retained in `outputs/e2_step8_unknown_inventory.csv`. The principal unknown case is 1,419,844 representatives (75.605%) without usable first/last history. Other exclusions and sensitivities are not discarded: catalog/template/bulk exclusions, copy-inclusive occurrences, repository capping, and history-quality categories remain in the Step 7 table.

Limitations and audit conclusions:

- The dataset exposes first and last available history fields, not complete middle-commit histories; maintenance is therefore based on observed endpoints plus a separately named any-observed-event signal.
- Explicit markers undercount agent work when a human commits agent-produced content or when commit messages omit generation metadata.
- Generic automation and `co-authored-by` markers can be ambiguous; the review retained 341 ambiguous rows rather than forcing them into human or agent classes.
- The high-level marker screen had perfect point estimates on the 387 determinate validation rows, but only six decisive positives; Wilson intervals were wide, so this does not establish population-wide precision.
- History coverage is highly uneven by location and cohort, so dated/canonical results cannot be generalized to the undated or skills-directory populations without qualification.
- Copy-inclusive and uncapped repository results are sensitivities because repeated content and high-volume repositories change the effective weighting.

The marker audit appendix is represented by the reason-code fields in the anonymized validation sample and the Step 5 label metrics; no author names, emails, repository-owner names, or raw commit messages are written to committed documentation. E2 execution is complete with the empirical-upper-bound limitation above explicitly preserved.

## Acceptance-criteria audit

- History denominators reconcile with E0: 458,137 representatives have fetched history, of which 457,985 fall inside the E0 dated cohort window.
- Marker definitions are versioned, reason-coded, and tested; the executed evidence uses identity, message, and content families.
- No raw author, email, repository-owner, or commit-message identity values are present in committed documentation or generated evidence outputs.
- The anonymized validation review is complete and reports per-signal performance with Wilson intervals, while retaining ambiguous cases separately.
- Creation, last-event maintenance, and any-observed-event maintenance remain separate throughout the estimates.
- Lower bounds and unknown/history coverage are reported. The expanded estimate remains equal to the lower bound, and the upper result is a theoretical ceiling because no empirical upper classifier was validated.
- Distinct-content, copy-inclusive, repository-capped, flag-exclusion, cohort, language, location, and history-quality sensitivities are reproducible from the listed scripts.
