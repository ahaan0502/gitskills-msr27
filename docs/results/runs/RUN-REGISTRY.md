# Experiment run registry

This registry gives every E3-E5 execution a stable, double-anonymous run ID. Run-specific methodology/results are recorded in this directory; large generated artifacts remain under the matching ignored `outputs/runs/<run-id>/` directory.

## Run ID convention

```text
<experiment>-r<number>-<purpose>
```

Examples include `E3-r01-primary` and `E3-r02-e6-stratified`. An E6 rerun keeps the original experiment identifier and records E6 as the triggering experiment and the primary run as its parent.

## Registry

| Run ID | Experiment | Purpose | Parent run | Status | Results record |
| --- | --- | --- | --- | --- | --- |
| `E3-r01-primary` | E3 | Primary structural convergence analysis | — | complete | [run record](E3-r01-primary.md) |
| `E4-r01-primary` | E4 | Primary phrasing convergence analysis | — | planned | [run record](E4-r01-primary.md) |
| `E5-r01-primary` | E5 | Primary topic coverage and semantic-diversity analysis | — | planned | [run record](E5-r01-primary.md) |

The E6-triggered reruns will receive new IDs when E6 is approved and scheduled, for example `E3-r02-e6-stratified`, `E4-r02-e6-stratified`, and `E5-r02-e6-stratified`. They will record the corresponding primary run as `Parent run` and will never overwrite it.

## Run rules

- A run ID is never reused.
- Each run has one committed Markdown record and one matching ignored output directory.
- Long-running runs use durable batch parts, progress logs, and completion markers; a final output without its completion marker is incomplete.
- Run records identify the data revision, methodology version, scripts, parameters, population, exclusions, outputs, validation, and limitations.
- Primary, sensitivity, and E6-stratified runs remain separate until final compilation.
- `docs/results/E3-results.md`, `E4-results.md`, and `E5-results.md` are cumulative result documents and should link back to the run records.
- No run record may contain author names, emails, repository-owner names, raw repository names, raw skill text, or raw commit messages.

Use [RUN-TEMPLATE.md](RUN-TEMPLATE.md) when creating a new run record.
