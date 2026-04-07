# SI 649 Final Project: Specimen Journey Dashboard

## 1. Project Overview

This project builds an interactive visualization dashboard for analyzing the hospital laboratory specimen journey. The dashboard is designed for hospital laboratory operations managers and quality improvement staff.

The working research/design question is:

**How does the specimen journey differ across cohorts, and where are the main delays and cancellation risks?**

The client asked for three main capabilities:

- Visualize the average time series of events for lab orders under selected filters.
- Compare two mutually exclusive groups through an A/B view.
- Show the likelihood of a named time-series event in that A/B comparison.

Our current dashboard focuses on operational workflow, not clinical result interpretation. It helps users inspect where orders slow down, where bottlenecks occur, and which subgroups may have higher risk of cancellation or long delays.

## 2. Data Meaning

The raw dataset is:

```text
Final Project- Case/2025_specimen_time_series_events_no_phi.tsv
```

Each raw row is an event, not a complete order. The most important fields are:

- `accession_id`: lab order ID.
- `test_code`: the ordered test code on a lab order.
- `pat_enc_csn_id`: patient encounter/contact ID.
- `pat_mrn_id`: patient ID.
- `barcode` and `tube_id`: specimen tube identifiers.
- `specimen_id`: specimen identifier.
- `test_performing_dept`: lab department performing the test.
- `event_street`: street-level event location.
- `event_source`: event source, usually `order` or `tube_tracker`.
- `event_type`: event name.
- `event_dt`: event timestamp.

The current pipeline mainly uses `event_source = order`, because the client request centers on order-level workflow timing.

Important order event types:

- `test_ordered_dt`: order placed.
- `test_collected_dt`: specimen collected.
- `test_receipt_dt`: specimen received by the lab.
- `test_min_resulted_dt` and `test_max_resulted_dt`: first and last resulted times.
- `test_min_verified_dt` and `test_max_verified_dt`: first and last verified times.
- `cancellation_dt`: cancellation event.

The raw data also includes `tube_tracker` events, which describe specimen tube movement and tube stops. Those events are useful for a future movement/path analysis, but they are not the main focus of the current dashboard MVP.

## 3. Current Analysis Logic

The raw event table is transformed into one row per ordered test.

Current ordered-test key:

```text
accession_id + test_code
```

This is used because the dataset explainer notes that ordered tests do not have a single unique ID column.

The processing script calculates:

- `hours_order_to_collect`
- `hours_collect_to_receipt`
- `hours_receipt_to_verified`
- `hours_order_to_verified`
- `hours_order_to_cancellation`
- `is_cancelled`
- `is_completed`
- `cohort_weekpart`, which is `Weekday` or `Weekend`
- `ordered_weekday_name`
- `analysis_in_scope`, currently based on 2025 orders
- `has_any_non_2025_event`, used to flag cross-year timestamp anomalies

The derived analysis table is:

```text
output/data/ordered_test_metrics.parquet
```

Current 2025-scope summary from the existing pipeline:

- Ordered tests in analysis scope: `230,245`
- Weekday cancellation rate: `4.28%`
- Weekend cancellation rate: `4.52%`
- Weekday median order-to-verified time: `1.75h`
- Weekend median order-to-verified time: `1.10h`

These are early descriptive results. Do not treat them as causal findings.

## 4. Repository Structure

Important files:

```text
README.md
app.py
requirements.txt
progress_report.tex
scripts/build_ordered_test_metrics.py
scripts/plot_weekday_weekend_summary.py
scripts/generate_sketches.py
Final Project Report Template-2.docx
Narrative Visualization Project Progress Check-in and Peer Critique.docx
Final Project- Case/Message from our Client.docx
Final Project- Case/SI 649 Extract Explainer.pdf
Final Project- Case/2025_specimen_time_series_events_no_phi.tsv
```

Generated outputs:

```text
output/data/ordered_test_metrics.parquet
output/data/weekday_vs_weekend_summary.csv
output/data/weekday_vs_weekend_stage_summary.csv
output/data/weekday_vs_weekend_summary.md
output/figures/weekday_vs_weekend_overview.png
output/sketches/sketch_1_dashboard_overview.png
output/sketches/sketch_2_average_journey_timeline.png
output/sketches/sketch_3_ab_comparison_and_risk.png
output/sketches/sketches_contact_sheet.png
```

Large raw data files should generally not be pushed to GitHub:

```text
Final Project- Case/2025_specimen_time_series_events_no_phi.tsv
Final Project- Case/2025_specimen_time_series_events_no_phi.zip
```

These are ignored by `.gitignore`.

## 5. Environment Setup

Use Python 3. Install dependencies with:

```bash
python3 -m pip install -r requirements.txt
```

The core dependencies are:

- `pandas`
- `pyarrow`
- `matplotlib`
- `pillow`
- `streamlit`
- `plotly`

If the derived parquet file already exists, you can run the dashboard immediately. If not, rebuild the data first.

## 6. How To Rebuild The Data

Run:

```bash
python3 scripts/build_ordered_test_metrics.py
```

This script reads:

```text
Final Project- Case/2025_specimen_time_series_events_no_phi.tsv
```

It generates:

```text
output/data/ordered_test_metrics.parquet
output/data/weekday_vs_weekend_summary.csv
output/data/weekday_vs_weekend_stage_summary.csv
output/data/weekday_vs_weekend_summary.md
```

If this step fails, check that the raw TSV exists in `Final Project- Case/`.

## 7. How To Generate Static Figures And Sketches

Generate the weekday-vs-weekend static figure:

```bash
MPLBACKEND=Agg MPLCONFIGDIR=tmp/mplconfig XDG_CACHE_HOME=tmp/xdgcache python3 scripts/plot_weekday_weekend_summary.py
```

Output:

```text
output/figures/weekday_vs_weekend_overview.png
```

Generate the low-fidelity sketch images:

```bash
MPLBACKEND=Agg MPLCONFIGDIR=tmp/mplconfig XDG_CACHE_HOME=tmp/xdgcache python3 scripts/generate_sketches.py
```

Outputs:

```text
output/sketches/sketch_1_dashboard_overview.png
output/sketches/sketch_2_average_journey_timeline.png
output/sketches/sketch_3_ab_comparison_and_risk.png
output/sketches/sketches_contact_sheet.png
```

The sketch images are intentionally low-fidelity digital wireframes. They are meant to communicate layout, encodings, and interaction ideas, not final UI polish.

## 8. How To Run The Interactive Dashboard

Run:

```bash
streamlit run app.py
```

Then open the local URL printed by Streamlit, usually:

```text
http://localhost:8501
```

The app reads:

```text
output/data/ordered_test_metrics.parquet
```

If the app says the derived analysis data is missing, run:

```bash
python3 scripts/build_ordered_test_metrics.py
```

## 9. Dashboard Guide

The dashboard has three main tabs:

### Overview

Use this tab to understand the current A/B comparison.

Main components:

- `Average Journey Timeline`: median milestone timing from order to verification.
- `A/B Snapshot`: ordered tests, completed tests, selected event rate, and median turnaround time.
- `Stage Duration Comparison`: median time spent in each workflow stage.
- `Event Likelihood`: rate of the selected risk event.
- `Current Read`: auto-generated narrative summary.

Use this tab to answer:

- Which cohort is faster or slower overall?
- Which stage creates the largest gap?
- Does the selected event happen more often in cohort A or cohort B?

### Hotspots

Use this tab to find categories with the largest differences.

Hotspot dimensions:

- `Test Code`
- `Event Street`
- `Performing Department`
- `Weekday Name`

This tab shows:

- largest turnaround-time gaps
- largest selected-event gaps
- a downloadable hotspot table

Use this tab to decide what insight is worth discussing in the final report.

### Details & Method

Use this tab to inspect example records and check method assumptions.

This tab includes:

- filtered details table
- CSV download
- method notes

Use this tab when a chart result looks surprising and you need to inspect the underlying records.

## 10. Dashboard Controls

### Filter Scope

These filters define the overall analysis population:

- `Exclude cross-year anomalies`
- `Test code`
- `Event street`
- `Performing department`
- `Completed tests only`

Recommended default:

- Keep `Exclude cross-year anomalies` checked.
- Leave `Completed tests only` unchecked unless you specifically want verified orders only.
- Start with no test/street/department filters, then narrow after finding a pattern.

### A/B Comparison

The comparison dimension controls what kind of cohorts are compared.

Available dimensions:

- `Weekpart`
- `Weekday Name`
- `Event Street`
- `Performing Department`
- `Test Code`

Default recommended first comparison:

```text
Weekpart: Weekday vs Weekend
```

Other useful comparisons:

- `Event Street`: compare two high-volume locations.
- `Performing Department`: compare two large departments.
- `Test Code`: compare two high-volume tests.

### Risk Event

Available event likelihood metrics:

- `Cancellation`
- `Long Order -> Collect`
- `Long Collect -> Receipt`
- `Long Receipt -> Verified`
- `Long Order -> Verified`

`Cancellation` uses the `cancellation_dt` event. The `Long ...` options use a p90 threshold within the current filtered comparison scope. For example, `Long Order -> Collect` means the order-to-collection duration is in the slowest 10% for the current scope.

## 11. Testing Checklist

Use this checklist before writing the final report.

### Basic app check

- Run `streamlit run app.py`.
- Confirm the app opens without errors.
- Confirm all three tabs load.
- Confirm the default charts appear.

### Default comparison check

- Keep `Weekpart`.
- Compare `Weekday` vs `Weekend`.
- Test `Cancellation`.
- Test each `Long ...` risk event.
- Write down which event creates the clearest story.

### Filter check

Try each filter individually:

- one `test_code`
- one `event_street`
- one `performing_department`
- `Completed tests only`
- cross-year anomaly exclusion on/off

Watch for:

- empty charts
- very small sample sizes
- confusing narrative summaries
- unexpectedly large deltas

### A/B comparison check

Try these comparison dimensions:

- `Weekpart`
- `Weekday Name`
- `Event Street`
- `Performing Department`
- `Test Code`

For each one, ask:

- Are both cohorts large enough?
- Is the comparison meaningful?
- Does the timeline support the story?
- Does the stage chart explain where the difference comes from?
- Does the event likelihood add anything useful?

### Hotspot check

In the `Hotspots` tab, test:

- `Test Code`
- `Event Street`
- `Performing Department`
- `Weekday Name`

For each hotspot table, look for:

- categories with strong TAT deltas
- categories with strong event-rate deltas
- categories with enough samples in both cohorts
- results that can be explained in plain language

### Main insight selection

After testing, fill in:

```text
Best comparison dimension:
Best Cohort A:
Best Cohort B:
Best risk event:
Most important stage gap:
Most useful hotspot dimension:
Most interesting hotspot category:
One-sentence final insight:
```

A strong final insight should satisfy:

- sample size is not tiny
- difference is visually clear
- explanation is understandable
- timeline, stage chart, and event likelihood support the same story

## 12. Final Report Writing Guide

Use `Final Project Report Template-2.docx` as the required structure. Suggested content for each section:

### 1. Executive Summary

Write a short non-technical overview:

- The project analyzes hospital lab specimen journeys.
- The dashboard supports cohort comparison and bottleneck detection.
- The key result should be based on the main insight selected after dashboard testing.

### 2. Domain Problem Characterization

Explain:

- Hospital lab orders involve ordering, collection, receipt, result reporting, and verification.
- Operational delays can affect turnaround time and workflow quality.
- Lab operations and quality improvement staff need tools to compare cohorts and identify bottlenecks.

### 3. Data & Task Abstraction

Describe:

- Raw data is an event log.
- The current analysis focuses on `order` events.
- One ordered test is approximated by `accession_id + test_code`.
- Important attributes include event timestamps, test code, event street, performing department, and cancellation status.

Use Munzner-style task language:

- compare cohorts
- summarize average timelines
- identify bottleneck stages
- locate high-risk categories
- browse details on demand

### 4. Visualization Design

Explain the dashboard views:

- timeline view uses position on a shared horizontal time scale
- stage duration comparison uses grouped bars
- event likelihood uses rate bars
- hotspot view uses ranked bars and tables
- color separates Cohort A and Cohort B

### 5. Dashboard Architecture

Describe the tabs:

- `Overview`: main A/B workflow summary
- `Hotspots`: subgroup discovery
- `Details & Method`: record inspection and method notes

Include screenshots from the Streamlit dashboard.

### 6. Narrative & Storytelling Layer

Explain:

- the dashboard generates a current-read summary
- annotations highlight stage gaps and turnaround deltas
- the final report should guide the reader through one chosen insight

### 7. Evaluation

If no formal user study is done, use heuristic evaluation:

- Does the dashboard answer the client requirements?
- Are visual encodings clear?
- Are filters understandable?
- Are sample sizes visible enough?
- Are risks of misinterpretation documented?

You can also include peer critique feedback if available.

### 8. Implementation Details

Mention:

- Python
- pandas
- Streamlit
- Plotly
- parquet output
- data-processing script
- filtering and p90 threshold logic

### 9. Ethical Considerations

Discuss:

- data is de-identified/no-PHI
- results should not be interpreted as causal
- small sample subgroup comparisons can mislead
- long-delay p90 thresholds are operational definitions, not clinical standards
- accessibility and color readability should be checked

### 10. Conclusion & Future Work

Mention future improvements:

- incorporate `tube_tracker` path analysis
- add more robust statistical checks
- improve narrative annotations
- validate with lab operations users
- refine filters and default cohorts

## 13. Suggested Team Workflow

Recommended next steps:

1. One teammate runs the dashboard and fills out the testing checklist.
2. One teammate chooses the main insight and screenshots the relevant dashboard views.
3. One teammate writes the final report sections using the guide above.
4. One teammate checks limitations, ethics, and method wording.
5. Everyone reviews whether the selected insight is clear and defensible.

When sharing findings, use this short template:

```text
Comparison:
Risk event:
Main visual evidence:
Most important stage gap:
Most important hotspot:
Why this matters for lab operations:
Limitations:
```

## 14. Known Limitations

- The dashboard currently focuses on order-level workflow events, not full tube-tracker movement paths.
- The A/B results are descriptive, not causal.
- The long-delay risk events use p90 thresholds from the current filtered scope.
- Some subgroup comparisons may be unstable if sample sizes are small.
- Final narrative should be selected after human review of the dashboard, not automatically accepted from the generated summary.

