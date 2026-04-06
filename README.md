# SI 649 Final Project

## Project Summary
This project designs a visualization dashboard for the laboratory specimen journey. The target users are hospital laboratory operations managers and quality improvement staff. The current working question is:

**How does the specimen journey differ across cohorts, and where are the main delays and cancellation risks?**

The first A/B comparison is:
- `Weekday` vs `Weekend`

The first event-likelihood metric is:
- `cancellation_dt`

## Current Status
The project already has:
- a defined scope and audience
- a progress-report draft in LaTeX
- three low-fidelity digital sketches
- a data-processing pipeline for ordered-test-level metrics
- an initial weekday-vs-weekend summary
- an initial static comparison figure
- a first interactive dashboard MVP

## Important Deadlines
- Progress report + sketches due: **Tuesday, April 7, 2026, 1:30 PM**
- Peer critique due: **Thursday, April 9, 2026, 1:30 PM**

## Key Files

### Assignment and source materials
- `Narrative Visualization Project Progress Check-in and Peer Critique.docx`
- `Final Project Report Template-2.docx`
- `Final Project- Case/Message from our Client.docx`
- `Final Project- Case/SI 649 Extract Explainer.pdf`
- `Final Project- Case/2025_specimen_time_series_events_no_phi.tsv`

### Report source
- `progress_report.tex`

### Scripts
- `app.py`
- `scripts/build_ordered_test_metrics.py`
- `scripts/plot_weekday_weekend_summary.py`
- `scripts/generate_sketches.py`
- `requirements.txt`

### Generated outputs
- `output/data/ordered_test_metrics.parquet`
- `output/data/weekday_vs_weekend_summary.csv`
- `output/data/weekday_vs_weekend_stage_summary.csv`
- `output/data/weekday_vs_weekend_summary.md`
- `output/figures/weekday_vs_weekend_overview.png`
- `output/sketches/sketch_1_dashboard_overview.png`
- `output/sketches/sketch_2_average_journey_timeline.png`
- `output/sketches/sketch_3_ab_comparison_and_risk.png`
- `output/sketches/sketches_contact_sheet.png`

## What Has Been Done

### 1. Scope definition
- Audience: hospital lab operations and quality improvement staff
- Main question: compare specimen journey delays and cancellation risk across cohorts
- First comparison: weekday vs weekend

### 2. Data preparation
The raw event table has been aggregated to one row per ordered test.

Derived fields include:
- order-to-collection time
- collection-to-receipt time
- receipt-to-verified time
- order-to-verified time
- cancellation flag
- weekday/weekend cohort

### 3. Initial findings
Current summary from the 2025 scope:
- Ordered tests in analysis scope: `230,245`
- Weekday cancellation rate: `4.28%`
- Weekend cancellation rate: `4.52%`
- Weekday median order-to-verified time: `1.75h`
- Weekend median order-to-verified time: `1.10h`

These are early descriptive results, not final causal conclusions.

### 4. Progress-report assets
Three low-fidelity digital wireframe sketches have already been created:
- overall dashboard layout
- average journey timeline option
- A/B comparison and cancellation-risk option

### 5. Final-dashboard MVP
An initial Streamlit dashboard now exists in `app.py`.

Current MVP features:
- filter by test code, event street, and performing department
- choose an A/B comparison dimension and two mutually exclusive cohorts
- choose a risk-event definition
- view an average journey timeline
- compare stage-level median durations
- compare cancellation likelihood
- read an auto-generated narrative summary
- inspect hotspot categories with the largest TAT or cancellation deltas
- download filtered details and hotspot tables
- inspect a details-on-demand table

## How To Reproduce The Current Outputs

### Build the ordered-test metrics
```bash
python3 scripts/build_ordered_test_metrics.py
```

### Generate the weekday-vs-weekend figure
```bash
MPLBACKEND=Agg MPLCONFIGDIR=tmp/mplconfig XDG_CACHE_HOME=tmp/xdgcache python3 scripts/plot_weekday_weekend_summary.py
```

### Generate the sketch images
```bash
MPLBACKEND=Agg MPLCONFIGDIR=tmp/mplconfig XDG_CACHE_HOME=tmp/xdgcache python3 scripts/generate_sketches.py
```

### Run the interactive dashboard
```bash
streamlit run app.py
```

## Which Code Generates Which Results

### Raw input
- `Final Project- Case/2025_specimen_time_series_events_no_phi.tsv`
  - main raw event dataset used by the current pipeline

### `scripts/build_ordered_test_metrics.py`
This script reads the raw TSV and aggregates order-level events into one row per ordered test.

It generates:
- `output/data/ordered_test_metrics.parquet`
  - ordered-test-level analysis table
- `output/data/weekday_vs_weekend_summary.csv`
  - cohort-level summary for `Weekday` vs `Weekend`
- `output/data/weekday_vs_weekend_stage_summary.csv`
  - stage-by-stage duration summary for `Weekday` vs `Weekend`
- `output/data/weekday_vs_weekend_summary.md`
  - short text summary of the current A/B results

### `scripts/plot_weekday_weekend_summary.py`
This script reads:
- `output/data/weekday_vs_weekend_summary.csv`
- `output/data/weekday_vs_weekend_stage_summary.csv`

It generates:
- `output/figures/weekday_vs_weekend_overview.png`
  - static figure showing stage-duration comparison and cancellation likelihood

### `scripts/generate_sketches.py`
This script generates the low-fidelity digital wireframe sketches used in the progress report.

It generates:
- `output/sketches/sketch_1_dashboard_overview.png`
  - full dashboard layout sketch
- `output/sketches/sketch_2_average_journey_timeline.png`
  - main timeline-view sketch
- `output/sketches/sketch_3_ab_comparison_and_risk.png`
  - A/B comparison and event-likelihood sketch
- `output/sketches/sketches_contact_sheet.png`
  - one combined image containing all three sketches

### `app.py`
This is the first interactive dashboard MVP for the final project.

It uses:
- `output/data/ordered_test_metrics.parquet`

It currently provides:
- base filtering
- A/B cohort selection
- switchable event-likelihood definitions
- average journey timeline view
- stage duration comparison
- cancellation-likelihood comparison
- hotspot analysis for subgroup gaps
- auto-generated story summary
- details-on-demand table

### `progress_report.tex`
This file is the draft progress report.

It uses:
- `output/sketches/sketch_1_dashboard_overview.png`
- `output/sketches/sketch_2_average_journey_timeline.png`
- `output/sketches/sketch_3_ab_comparison_and_risk.png`

It generates:
- the final progress-report PDF, once compiled in a LaTeX environment

## Progress Report Notes
- `progress_report.tex` already includes the three sketch images.
- The report treats the sketches as low-fidelity digital wireframes, not polished mockups.
- `pdflatex` was not available in the current environment, so the `.tex` file was written but not compiled locally.

## What Still Needs To Be Done

### Before the progress-check deadline
- compile `progress_report.tex` into PDF
- confirm the report fits on one page
- review wording as a team
- decide whether to keep the digital sketches as-is or replace them with hand-drawn versions

### For the final project
- refine the current interactive dashboard MVP
- improve comparison options beyond the first cohort setup
- expand event-likelihood exploration beyond `cancellation_dt` if the data model supports it
- add narrative annotations and storytelling structure
- evaluate the design
- write the final report

## Suggested Team Discussion
When sharing this repo with teammates, review:
- whether the current scope is the right one
- whether `weekday vs weekend` is the best first A/B comparison
- whether the current sketches are clear enough
- who will own dashboard implementation
- who will own report editing and final submission
