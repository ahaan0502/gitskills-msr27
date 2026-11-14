# `<RUN-ID>`

Status: planned

## Run identity

- Experiment:
- Purpose:
- Parent run:
- Triggering experiment, if any:
- Created:
- Data revision:
- Methodology version:

## Objective and scope

Describe the question addressed by this run and whether it is primary, sensitivity, or an E6-stratified rerun.

## Inputs and parameters

- Input tables/derived tables:
- Scripts/modules:
- Parameters:
- Population and unit of analysis:
- Cohort/date restrictions:
- Reuse of prior run outputs:

## Exclusions and safeguards

Record parser/status exclusions, missingness, small-cell rules, anonymization checks, and any reasons the run is not directly comparable with another run.

## Outputs

List ignored files under `outputs/runs/<RUN-ID>/`. Do not commit generated Parquet, SQLite, CSV, database, or other large artifacts.

For long-running extraction, also record the batch-part directory, progress log, completion marker, and final row/distinct-key verification. Treat the final output as incomplete unless the completion marker exists.

## Results

Add summarized counts, rates, intervals, tables, and interpretation after execution. Link to the cumulative experiment result document when compiled.

## Validation and reproducibility

Record tests, schema/count checks, commands, software/version pins, and any rerun comparison checks.

## Limitations

State uncertainty, data-coverage limitations, sensitivity caveats, and what this run does not establish.
