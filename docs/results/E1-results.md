# E1 results - natural-language distribution

Status: complete.

## Step 1 - text inputs and population

The analysis used one row per distinct file_sha from the E0-derived skills table. The three text units were description (fm_description), body prose (body_prose, excluding headings and fenced code), and paragraphs reconstructed from representative raw content with Markdown block parsing, excluding headings, code, and empty blocks.

The full population contained 1,877,981 distinct contents. There were 1,698,745 non-empty descriptions, 1,864,319 non-empty body-prose fields, 6,138 symlink-like records, 44,838 parser-error records, and 2 empty records. After structural and parse-error exclusions, 1,654,422 descriptions and 1,819,580 body-prose fields were eligible. The short-text counts were 8,923 descriptions and 9,147 body fields.

## Step 2 - text-quality rules

Null and whitespace-only fields were treated as missing. Empty, symlink-like, and parser-error records were excluded from primary field estimates. Short text was retained and marked: fewer than 20 Unicode characters for descriptions and fewer than 50 for body prose. Descriptions and bodies were detected independently. Unknown, short-text, mixed-language, missing, parse-error, and structural-exclusion outcomes remain explicit rather than being silently dropped.

## Step 3 - detector configuration

The detector was lingua-language-detector version 2.2.0, with 75 bundled languages. Configuration used LanguageDetectorBuilder.from_all_languages().with_minimum_relative_distance(0.15).build(). The minimum relative distance is an abstention threshold, not a calibrated probability. Relative confidence values were retained for auditability.

## Step 4 - full detection output

outputs/e1_language.parquet contains 1,877,981 rows and 11 columns. It contains 85,845,295 reconstructed paragraphs, averaging 45.71 paragraphs per skill with a maximum of 21,763.

Description statuses: detected 1,622,711; short_text 4,249; short_text_unknown 4,685; unknown 22,777; missing 172,581; excluded_parse_error 44,838; excluded_structural 6,140.

Body statuses: detected 1,809,272; short_text 6,430; short_text_unknown 2,717; unknown 1,161; missing 7,423; excluded_parse_error 44,838; excluded_structural 6,140.

## Step 5 - complete overall language shares

The description and body denominators are 1,877,981 distinct skills. The paragraph denominator is 85,845,295 reconstructed paragraphs. Percentages below are calculated from the corresponding denominator; every nonzero language row in the generated output is included.

### description
| Language | n | share |
| --- | ---: | ---: |
| `en` | 1424623 | 75.859% |
| `unknown_or_undetermined` | 251021 | 13.367% |
| `zh` | 85552 | 4.556% |
| `de` | 27515 | 1.465% |
| `ja` | 25075 | 1.335% |
| `ko` | 14936 | 0.795% |
| `pt` | 14692 | 0.782% |
| `es` | 11376 | 0.606% |
| `fr` | 4776 | 0.254% |
| `ru` | 3979 | 0.212% |
| `tr` | 3599 | 0.192% |
| `la` | 3146 | 0.168% |
| `vi` | 1828 | 0.097% |
| `tl` | 836 | 0.045% |
| `it` | 760 | 0.040% |
| `pl` | 654 | 0.035% |
| `nl` | 518 | 0.028% |
| `id` | 470 | 0.025% |
| `th` | 452 | 0.024% |
| `cs` | 211 | 0.011% |
| `ar` | 200 | 0.011% |
| `sv` | 181 | 0.010% |
| `nb` | 175 | 0.009% |
| `uk` | 164 | 0.009% |
| `ca` | 156 | 0.008% |
| `da` | 151 | 0.008% |
| `he` | 114 | 0.006% |
| `fi` | 108 | 0.006% |
| `nn` | 107 | 0.006% |
| `ro` | 95 | 0.005% |
| `eo` | 70 | 0.004% |
| `sk` | 45 | 0.002% |
| `fa` | 40 | 0.002% |
| `cy` | 33 | 0.002% |
| `xh` | 28 | 0.001% |
| `hu` | 28 | 0.001% |
| `ms` | 23 | 0.001% |
| `ts` | 23 | 0.001% |
| `tn` | 22 | 0.001% |
| `el` | 18 | 0.001% |
| `st` | 17 | 0.001% |
| `hr` | 16 | 0.001% |
| `et` | 15 | 0.001% |
| `bg` | 14 | 0.001% |
| `yo` | 14 | 0.001% |
| `af` | 11 | 0.001% |
| `sn` | 10 | 0.001% |
| `sw` | 9 | 0.000% |
| `so` | 9 | 0.000% |
| `az` | 7 | 0.000% |
| `bs` | 7 | 0.000% |
| `sq` | 5 | 0.000% |
| `mi` | 5 | 0.000% |
| `lt` | 4 | 0.000% |
| `eu` | 4 | 0.000% |
| `is` | 4 | 0.000% |
| `ga` | 4 | 0.000% |
| `sl` | 4 | 0.000% |
| `zu` | 3 | 0.000% |
| `hi` | 3 | 0.000% |
| `mr` | 3 | 0.000% |
| `te` | 2 | 0.000% |
| `sr` | 2 | 0.000% |
| `ur` | 2 | 0.000% |
| `ta` | 2 | 0.000% |
| `kk` | 1 | 0.000% |
| `bn` | 1 | 0.000% |
| `pa` | 1 | 0.000% |
| `lg` | 1 | 0.000% |
| `mn` | 1 | 0.000% |
### body_prose
| Language | n | share |
| --- | ---: | ---: |
| `en` | 1572984 | 83.759% |
| `zh` | 107466 | 5.722% |
| `unknown_or_undetermined` | 62279 | 3.316% |
| `ja` | 30362 | 1.617% |
| `de` | 28348 | 1.509% |
| `pt` | 17913 | 0.954% |
| `ko` | 17888 | 0.953% |
| `es` | 14540 | 0.774% |
| `fr` | 6545 | 0.349% |
| `ru` | 4667 | 0.249% |
| `tr` | 3406 | 0.181% |
| `vi` | 2504 | 0.133% |
| `ar` | 1573 | 0.084% |
| `it` | 1140 | 0.061% |
| `tl` | 912 | 0.049% |
| `pl` | 878 | 0.047% |
| `id` | 712 | 0.038% |
| `nl` | 659 | 0.035% |
| `th` | 482 | 0.026% |
| `la` | 452 | 0.024% |
| `cs` | 305 | 0.016% |
| `nb` | 269 | 0.014% |
| `sv` | 222 | 0.012% |
| `uk` | 183 | 0.010% |
| `he` | 167 | 0.009% |
| `ca` | 159 | 0.008% |
| `ro` | 133 | 0.007% |
| `da` | 133 | 0.007% |
| `fi` | 132 | 0.007% |
| `yo` | 83 | 0.004% |
| `hu` | 64 | 0.003% |
| `eo` | 57 | 0.003% |
| `sk` | 52 | 0.003% |
| `hr` | 50 | 0.003% |
| `fa` | 26 | 0.001% |
| `nn` | 22 | 0.001% |
| `el` | 21 | 0.001% |
| `cy` | 19 | 0.001% |
| `et` | 17 | 0.001% |
| `hi` | 15 | 0.001% |
| `bg` | 13 | 0.001% |
| `bs` | 12 | 0.001% |
| `mi` | 10 | 0.001% |
| `lt` | 10 | 0.001% |
| `sn` | 9 | 0.000% |
| `sw` | 8 | 0.000% |
| `lv` | 6 | 0.000% |
| `xh` | 6 | 0.000% |
| `sl` | 6 | 0.000% |
| `sr` | 6 | 0.000% |
| `sq` | 5 | 0.000% |
| `eu` | 4 | 0.000% |
| `mr` | 4 | 0.000% |
| `is` | 4 | 0.000% |
| `ms` | 4 | 0.000% |
| `bn` | 4 | 0.000% |
| `st` | 4 | 0.000% |
| `ur` | 3 | 0.000% |
| `pa` | 3 | 0.000% |
| `az` | 3 | 0.000% |
| `kk` | 3 | 0.000% |
| `ts` | 3 | 0.000% |
| `te` | 3 | 0.000% |
| `ta` | 2 | 0.000% |
| `so` | 2 | 0.000% |
| `tn` | 2 | 0.000% |
| `zu` | 1 | 0.000% |
| `af` | 1 | 0.000% |
| `lg` | 1 | 0.000% |
### paragraph
| Language | n | share |
| --- | ---: | ---: |
| `en` | 63276882 | 73.710% |
| `unknown_or_undetermined` | 12613799 | 14.694% |
| `zh` | 5074706 | 5.911% |
| `ja` | 1020451 | 1.189% |
| `de` | 897659 | 1.046% |
| `pt` | 624597 | 0.728% |
| `ko` | 609817 | 0.710% |
| `es` | 418292 | 0.487% |
| `fr` | 298714 | 0.348% |
| `la` | 266701 | 0.311% |
| `ru` | 151616 | 0.177% |
| `tr` | 90402 | 0.105% |
| `vi` | 77868 | 0.091% |
| `it` | 43905 | 0.051% |
| `pl` | 39768 | 0.046% |
| `nl` | 32551 | 0.038% |
| `ar` | 29616 | 0.034% |
| `tl` | 24524 | 0.029% |
| `ca` | 22997 | 0.027% |
| `th` | 22374 | 0.026% |
| `id` | 17100 | 0.020% |
| `cy` | 16287 | 0.019% |
| `sv` | 12472 | 0.015% |
| `xh` | 11817 | 0.014% |
| `st` | 11509 | 0.013% |
| `ro` | 9465 | 0.011% |
| `cs` | 8956 | 0.010% |
| `he` | 8747 | 0.010% |
| `da` | 7952 | 0.009% |
| `eo` | 7347 | 0.009% |
| `tn` | 7007 | 0.008% |
| `fi` | 6753 | 0.008% |
| `nb` | 6630 | 0.008% |
| `uk` | 6619 | 0.008% |
| `nn` | 6397 | 0.007% |
| `yo` | 6116 | 0.007% |
| `so` | 5813 | 0.007% |
| `ts` | 5070 | 0.006% |
| `hu` | 4936 | 0.006% |
| `sw` | 4181 | 0.005% |
| `et` | 3855 | 0.004% |
| `mi` | 3647 | 0.004% |
| `ga` | 2846 | 0.003% |
| `sn` | 2707 | 0.003% |
| `sk` | 2251 | 0.003% |
| `af` | 2228 | 0.003% |
| `ms` | 2042 | 0.002% |
| `sq` | 2027 | 0.002% |
| `lv` | 1935 | 0.002% |
| `bg` | 1374 | 0.002% |
| `el` | 1094 | 0.001% |
| `lg` | 1078 | 0.001% |
| `zu` | 1021 | 0.001% |
| `lt` | 971 | 0.001% |
| `is` | 959 | 0.001% |
| `az` | 836 | 0.001% |
| `fa` | 801 | 0.001% |
| `eu` | 764 | 0.001% |
| `bs` | 672 | 0.001% |
| `hi` | 637 | 0.001% |
| `sl` | 487 | 0.001% |
| `hr` | 476 | 0.001% |
| `kk` | 289 | 0.000% |
| `sr` | 272 | 0.000% |
| `mn` | 227 | 0.000% |
| `bn` | 223 | 0.000% |
| `mr` | 223 | 0.000% |
| `ur` | 202 | 0.000% |
| `mk` | 184 | 0.000% |
| `te` | 163 | 0.000% |
| `pa` | 146 | 0.000% |
| `ta` | 137 | 0.000% |
| `be` | 101 | 0.000% |
| `ka` | 6 | 0.000% |
| `gu` | 1 | 0.000% |

ISO 639-1 codes are used where available; unknown_or_undetermined is the explicit detector-abstention/unknown category.

## Step 6 - cohort results

Cohorts use E0-valid first-commit dates from October 2025 through July 2026. Undated and pre-window records are excluded from the cohort tables rather than assigned a month. The generated cohort output contains 300 description rows, 287 body-prose rows, and 619 paragraph rows across the ten cohorts. The largest skill denominator is 86,254 and the largest paragraph denominator is 3,600,390.

The cohort summary for every unit and month is:

| Unit | Cohort | Denominator | English n (%) | Unknown n (%) |
| --- | --- | ---: | ---: | ---: |
| description | 2025-10 | 1,265 | 1,062 (83.953%) | 118 (9.328%) |
| description | 2025-11 | 3,578 | 2,973 (83.091%) | 436 (12.186%) |
| description | 2025-12 | 6,615 | 5,288 (79.940%) | 813 (12.290%) |
| description | 2026-01 | 20,918 | 16,835 (80.481%) | 2,169 (10.369%) |
| description | 2026-02 | 49,234 | 32,682 (66.381%) | 12,596 (25.584%) |
| description | 2026-03 | 78,540 | 62,304 (79.328%) | 8,275 (10.536%) |
| description | 2026-04 | 84,062 | 63,941 (76.064%) | 10,680 (12.705%) |
| description | 2026-05 | 86,254 | 68,041 (78.884%) | 8,463 (9.812%) |
| description | 2026-06 | 85,855 | 64,461 (75.081%) | 8,129 (9.468%) |
| description | 2026-07 | 41,664 | 33,233 (79.764%) | 3,169 (7.606%) |
| body_prose | 2025-10 | 1,265 | 1,150 (90.909%) | 28 (2.213%) |
| body_prose | 2025-11 | 3,578 | 3,276 (91.560%) | 82 (2.292%) |
| body_prose | 2025-12 | 6,615 | 5,758 (87.045%) | 201 (3.039%) |
| body_prose | 2026-01 | 20,918 | 18,007 (86.084%) | 530 (2.534%) |
| body_prose | 2026-02 | 49,234 | 43,217 (87.779%) | 1,325 (2.691%) |
| body_prose | 2026-03 | 78,540 | 66,624 (84.828%) | 2,078 (2.646%) |
| body_prose | 2026-04 | 84,062 | 68,994 (82.075%) | 3,541 (4.212%) |
| body_prose | 2026-05 | 86,254 | 70,456 (81.684%) | 4,069 (4.717%) |
| body_prose | 2026-06 | 85,855 | 67,702 (78.856%) | 4,402 (5.127%) |
| body_prose | 2026-07 | 41,664 | 33,655 (80.777%) | 1,844 (4.426%) |
| paragraph | 2025-10 | 101,967 | 74,887 (73.442%) | 21,914 (21.491%) |
| paragraph | 2025-11 | 298,037 | 215,495 (72.305%) | 65,575 (22.002%) |
| paragraph | 2025-12 | 326,510 | 230,362 (70.553%) | 70,130 (21.479%) |
| paragraph | 2026-01 | 987,308 | 701,136 (71.015%) | 195,547 (19.806%) |
| paragraph | 2026-02 | 2,137,551 | 1,613,415 (75.480%) | 363,950 (17.026%) |
| paragraph | 2026-03 | 3,166,689 | 2,323,155 (73.362%) | 511,090 (16.140%) |
| paragraph | 2026-04 | 3,496,960 | 2,568,970 (73.463%) | 508,524 (14.542%) |
| paragraph | 2026-05 | 3,600,390 | 2,625,789 (72.931%) | 535,832 (14.883%) |
| paragraph | 2026-06 | 3,163,691 | 2,338,915 (73.930%) | 377,762 (11.941%) |
| paragraph | 2026-07 | 1,604,388 | 1,221,950 (76.163%) | 176,079 (10.975%) |

The underlying output also contains every non-English language row for every cohort.

## Step 7 - description/body agreement

Strict agreement requires both fields to have status detected:

| Definition | Skills compared | Agree | Agreement |
| --- | ---: | ---: | ---: |
| Detected labels only | 1,612,318 | 1,560,442 | 96.783% |
| Detected plus short-text labels | 1,620,525 | 1,567,877 | 96.751% |

Description labels were unavailable or undetermined for 251,021 skills; body labels were unavailable or undetermined for 62,279. Among 1,818,458 skills with paragraphs, 472,031 (25.958%) had more than one detected paragraph language. The full disagreement matrix is in the ignored outputs/e1_description_body_matrix.csv.

The complete agreement accounting was:

| Metric | n | Denominator | Rate |
| --- | ---: | ---: | ---: |
| Agree, both confident | 1,560,442 | 1,612,318 | 96.783% |
| Agree, including short text | 1,567,877 | 1,620,525 | 96.751% |
| Body-only labeled | 195,177 | 1,877,981 | 10.393% |
| Body unknown/undetermined | 62,279 | 1,877,981 | 3.316% |
| Both confident | 1,612,318 | 1,877,981 | 85.854% |
| Both labeled including short text | 1,620,525 | 1,877,981 | 86.291% |
| Description-only labeled | 6,435 | 1,877,981 | 0.343% |
| Description unknown/undetermined | 251,021 | 1,877,981 | 13.367% |
| Neither labeled | 55,844 | 1,877,981 | 2.974% |
| Paragraph mixed language | 472,031 | 1,818,458 | 25.958% |

## Step 8 - sensitivity analyses

| View | English description | English body | Strict agreement |
| --- | ---: | ---: | ---: |
| Distinct-content baseline | 75.859% | 83.759% | 96.783% |
| Copy-inclusive occurrences | 81.941% | 88.312% | 97.534% |

Copy-inclusive agreement used 3,376,103 confident occurrence pairs. Across E0 flag strata, strict agreement ranged from 96.506% (bulk_repo_false) to 97.169% (template_true); catalog_true was 97.143%. Paragraph sensitivity was not repeated across every copy/flag stratum because that would replicate the 85.8 million paragraph unit for each view.

The complete agreement sensitivity table was:

| View | Rows | Confident pairs | Agree | Agreement |
| --- | ---: | ---: | ---: | ---: |
| bulk_repo_false | 966,525 | 870,070 | 839,672 | 96.506% |
| bulk_repo_true | 911,456 | 742,248 | 720,770 | 97.106% |
| catalog_false | 1,759,927 | 1,506,229 | 1,457,384 | 96.757% |
| catalog_true | 118,054 | 106,089 | 103,058 | 97.143% |
| copy_inclusive | 1,877,981 occurrences / 3,797,117 denominator | 3,376,103 | 3,292,839 | 97.534% |
| distinct_content | 1,877,981 | 1,612,318 | 1,560,442 | 96.783% |
| template_false | 1,689,909 | 1,438,246 | 1,391,298 | 96.736% |
| template_true | 188,072 | 174,072 | 169,144 | 97.169% |

English and unknown/undetermined sensitivity shares for every view were:

| View | Unit | Denominator | English n (%) | Unknown n (%) |
| --- | --- | ---: | ---: | ---: |
| bulk_repo_false | description | 966,525 | 763,934 (79.039%) | 89,763 (9.287%) |
| bulk_repo_false | body_prose | 966,525 | 797,839 (82.547%) | 28,750 (2.975%) |
| bulk_repo_true | description | 911,456 | 660,689 (72.487%) | 161,258 (17.692%) |
| bulk_repo_true | body_prose | 911,456 | 775,145 (85.045%) | 33,529 (3.679%) |
| catalog_false | description | 1,759,927 | 1,328,135 (75.465%) | 240,059 (13.640%) |
| catalog_false | body_prose | 1,759,927 | 1,470,178 (83.536%) | 59,808 (3.398%) |
| catalog_true | description | 118,054 | 96,488 (81.732%) | 10,962 (9.286%) |
| catalog_true | body_prose | 118,054 | 102,806 (87.084%) | 2,471 (2.093%) |
| copy_inclusive | description | 3,797,117 | 3,111,410 (81.941%) | 390,948 (10.296%) |
| copy_inclusive | body_prose | 3,797,117 | 3,353,291 (88.312%) | 102,491 (2.699%) |
| distinct_content | description | 1,877,981 | 1,424,623 (75.859%) | 251,021 (13.367%) |
| distinct_content | body_prose | 1,877,981 | 1,572,984 (83.759%) | 62,279 (3.316%) |
| template_false | description | 1,689,909 | 1,255,993 (74.323%) | 240,073 (14.206%) |
| template_false | body_prose | 1,689,909 | 1,396,641 (82.646%) | 56,996 (3.373%) |
| template_true | description | 188,072 | 168,630 (89.662%) | 10,948 (5.821%) |
| template_true | body_prose | 188,072 | 176,343 (93.764%) | 5,283 (2.809%) |

## Step 9 - detector validation

The corrected validation frame used metadata-only stratification followed by streaming retrieval of selected text. It sampled by field, E0 cohort, short/medium/long length, and selected predicted labels: English, Chinese, Japanese, German, and unknown/undetermined. The 301-row reference-labeled sample produced 293 exact matches (97.342%). The Wilson 95% interval was 94.844% to 98.647%.

| Label | Precision | Recall | Support |
| --- | ---: | ---: | ---: |
| German | 89.13% | 100.00% | 41 |
| English | 100.00% | 92.96% | 71 |
| Japanese | 100.00% | 100.00% | 63 |
| Chinese | 100.00% | 100.00% | 62 |
| Unknown/undetermined | 95.31% | 100.00% | 61 |

French and Vietnamese appeared only as detector misses in this focused validation sample and had insufficient support for reliable per-class estimates. The interval describes the validation sample; it is not a calibrated uncertainty interval for every language in the corpus.

## Step 10 - reproducibility and output inventory

Commands used:

```text
python scripts/05_e1_detect_language.py --overwrite
python scripts/06_e1_overall_language.py
python scripts/07_e1_cohort_language.py
python scripts/08_e1_description_body_agreement.py
python scripts/09_e1_sensitivities.py
python scripts/10_e1_validate_detector.py --per-cell 1
python scripts/10_e1_validate_detector.py --apply-reference-labels
python scripts/10_e1_validate_detector.py --score
```

Ignored generated outputs: e1_language.parquet; e1_overall_language_shares.csv; e1_cohort_language_shares.csv; e1_description_body_agreement.csv; e1_description_body_matrix.csv; e1_sensitivity_language.csv; e1_sensitivity_agreement.csv; e1_hand_label_sample.csv.

The committed methodology and execution plan are in experiments/E1.md. E1 does not analyze authorship, structural convergence, phrasing, semantic topics, or integration effects; those belong to E2-E6.

Complete row-level appendices from the ignored tabular outputs are preserved in [the cohort table](E1-cohort-table.md), [the sensitivity table](E1-sensitivity-table.md), and [the agreement tables](E1-agreement-tables.md).

