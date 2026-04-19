# SI 649 Final Project: Specimen Journey Comparison Dashboard Code

This repository contains the code used to process data, generate figures, and produce the interactive dashboard for the SI 649 final project.

## Project files

- `app.py`: The streamlit dashboard
- `scripts/build_ordered_test_metrics.py`: Builds the derived ordered-test dataset from the raw TSV
- `scripts/plot_weekday_weekend_summary.py`: Builds the static weekday-vs-weekend summary plot
- `scripts/generate_report_assets.py`: Builds the reproducible figures and summary files used in the final report
- `requirements.txt`: Python dependencies

## Data Requirement

The raw dataset must be present at:
```text
Final Project- Case/2025_specimen_time_series_events_no_phi.tsv
```
This is the input to the data-processing pipeline.

## Environment setup

Create a Python 3 environment and install dependencies with:
```bash
python3 -m pip install -r requirements.txt
```

## How To Run The Code

### 1. Build the Derived Analysis Dataset

Run:
```bash
python3 scripts/build_ordered_test_metrics.py
```
This will read the raw TSV and produce:
```text
output/data/ordered_test_metrics.parquet
output/data/weekday_vs_weekend_summary.csv
output/data/weekday_vs_weekend_stage_summary.csv
output/data/weekday_vs_weekend_summary.md
```

### 2. Generate Static Analysis Figures

Run:
```bash
MPLBACKEND=Agg MPLCONFIGDIR=tmp/mplconfig XDG_CACHE_HOME=tmp/xdgcache python3 scripts/plot_weekday_weekend_summary.py
```
This will generate:
```text
output/figures/weekday_vs_weekend_overview.png
```

### 3. Generate Final Report Figures and Summary Assets

Run:
```bash
MPLBACKEND=Agg MPLCONFIGDIR=tmp/mplconfig XDG_CACHE_HOME=tmp/xdgcache python3 scripts/generate_report_assets.py
```
This will generate:
```text
output/report/eda_event_sources.png
output/report/eda_order_event_types.png
output/report/eda_key_missingness.png
output/report/eda_stage_duration_distributions.png
output/report/viz_average_timeline_weekpart.png
output/report/viz_stage_comparison_weekpart.png
output/report/viz_event_likelihood_long_order_collect_weekpart.png
output/report/viz_event_likelihood_long_receipt_to_verified_weekpart.png
output/report/viz_hotspots_event_street_long_order_collect.png
output/report/viz_hotspots_event_street_long_receipt_to_verified.png
output/report/report_facts.md
```

### 4. Run The Interactive Dashboard

Run:
```bash
streamlit run app.py
```
Then visit the local URL printed by Streamlit, usually:
```text
http://localhost:8501
```
The dashboard will read:
```text
output/data/ordered_test_metrics.parquet
```

## Recommended End-to-End Reproduction Order.

If you would like to reproduce the full project from raw data, please execute the steps above in this order.
```bash
python3 -m pip install -r requirements.txt
python3 scripts/build_ordered_test_metrics.py
MPLBACKEND=Agg MPLCONFIGDIR=tmp/mplconfig XDG_CACHE_HOME=tmp/xdgcache python3 scripts/plot_weekday_weekend_summary.py
MPLBACKEND=Agg MPLCONFIGDIR=tmp/mplconfig XDG_CACHE_HOME=tmp/xdxcache python3 scripts/generate_report_assets.py
streamlit run app.py
```

## Notes.

- The dashboard is currently implemented to operate on one row per ordered test (using `accession_id + test_code`).
- The current dashboard is implemented to work on order-level workflow events, not for full `tube_tracker` path reconstruction.
- If the dashboard does not start, first make sure that `output/data/ordered_test_metrics.parquet` is present.

## Troubleshooting.

- If `build_ordered_test_metrics.py` does not start, please first make sure that the raw TSV is present in `Final Project- Case/`.
- If `streamlit run app.py` cannot start because the parquet file is missing, please re-build the dataset first.
- The `MPLBACKEND` and `MPLCONFIGDIR` and `XDG_CACHE_HOME` lines are present in the figure-generation commands and are to avoid issues with the local Matplotlib cache.