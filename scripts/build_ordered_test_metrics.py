#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd


ORDER_EVENT_TYPES = [
    "test_ordered_dt",
    "test_collected_dt",
    "test_receipt_dt",
    "test_min_resulted_dt",
    "test_max_resulted_dt",
    "test_min_verified_dt",
    "test_max_verified_dt",
    "cancellation_dt",
]

IDENTITY_FIELDS = [
    "accession_id",
    "pat_enc_csn_id",
    "pat_mrn_id",
    "barcode",
    "tube_id",
    "specimen_id",
    "test_code",
    "test_performing_dept",
    "test_performing_location",
    "event_street",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate order-level lab events into one row per ordered test and "
            "generate weekday versus weekend summaries."
        )
    )
    parser.add_argument(
        "--input",
        default="Final Project- Case/2025_specimen_time_series_events_no_phi.tsv",
        help="Path to the raw TSV extract.",
    )
    parser.add_argument(
        "--output-dir",
        default="output/data",
        help="Directory where derived files should be written.",
    )
    return parser.parse_args()


def empty_record_from_row(row: dict[str, str]) -> dict[str, str]:
    record = {field: row.get(field, "") for field in IDENTITY_FIELDS}
    for event_name in ORDER_EVENT_TYPES:
        record[event_name] = ""
    return record


def update_record(record: dict[str, str], row: dict[str, str]) -> None:
    for field in IDENTITY_FIELDS:
        if not record[field] and row.get(field):
            record[field] = row[field]

    event_type = row["event_type"]
    event_dt = row["event_dt"]

    if event_type not in ORDER_EVENT_TYPES or not event_dt:
        return

    current = record[event_type]
    if not current or event_dt < current:
        record[event_type] = event_dt


def build_ordered_test_frame(input_path: Path) -> pd.DataFrame:
    records: dict[tuple[str, str], dict[str, str]] = {}

    with input_path.open("r", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            if row["event_source"] != "order":
                continue

            key = (row["accession_id"], row["test_code"])
            record = records.get(key)
            if record is None:
                record = empty_record_from_row(row)
                records[key] = record
            update_record(record, row)

    return pd.DataFrame(records.values())


def add_datetime_and_duration_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in ORDER_EVENT_TYPES:
        df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")

    df["first_resulted_dt"] = df["test_min_resulted_dt"].combine_first(
        df["test_max_resulted_dt"]
    )
    df["final_resulted_dt"] = df["test_max_resulted_dt"].combine_first(
        df["test_min_resulted_dt"]
    )
    df["first_verified_dt"] = df["test_min_verified_dt"].combine_first(
        df["test_max_verified_dt"]
    )
    df["final_verified_dt"] = df["test_max_verified_dt"].combine_first(
        df["test_min_verified_dt"]
    )

    event_years = pd.DataFrame(
        {col: df[col].dt.year for col in ORDER_EVENT_TYPES},
        index=df.index,
    )
    df["ordered_year"] = df["test_ordered_dt"].dt.year
    df["analysis_in_scope"] = df["ordered_year"].eq(2025)
    df["has_any_non_2025_event"] = (
        event_years.notna() & event_years.ne(2025)
    ).any(axis=1)

    df["ordered_weekday_name"] = df["test_ordered_dt"].dt.day_name()
    df["ordered_dayofweek"] = df["test_ordered_dt"].dt.dayofweek
    df["cohort_weekpart"] = df["ordered_dayofweek"].map(
        lambda x: "Weekend" if pd.notna(x) and int(x) >= 5 else "Weekday"
    )
    df["is_cancelled"] = df["cancellation_dt"].notna()
    df["is_completed"] = df["final_verified_dt"].notna()

    duration_specs = {
        "hours_order_to_collect": ("test_ordered_dt", "test_collected_dt"),
        "hours_collect_to_receipt": ("test_collected_dt", "test_receipt_dt"),
        "hours_receipt_to_verified": ("test_receipt_dt", "final_verified_dt"),
        "hours_order_to_verified": ("test_ordered_dt", "final_verified_dt"),
        "hours_order_to_cancellation": ("test_ordered_dt", "cancellation_dt"),
    }

    for output_col, (start_col, end_col) in duration_specs.items():
        df[output_col] = (
            df[end_col] - df[start_col]
        ).dt.total_seconds() / 3600.0
        invalid = df[output_col] < 0
        df.loc[invalid, output_col] = pd.NA

    return df


def build_stage_summary(df: pd.DataFrame) -> pd.DataFrame:
    analysis = df[df["analysis_in_scope"]].copy()

    metrics = [
        ("hours_order_to_collect", "order_to_collect"),
        ("hours_collect_to_receipt", "collect_to_receipt"),
        ("hours_receipt_to_verified", "receipt_to_verified"),
        ("hours_order_to_verified", "order_to_verified"),
    ]

    rows: list[dict[str, object]] = []
    for cohort, cohort_df in analysis.groupby("cohort_weekpart", dropna=False):
        for source_col, stage_name in metrics:
            valid = cohort_df[source_col].dropna()
            rows.append(
                {
                    "cohort": cohort,
                    "stage": stage_name,
                    "available_records": int(valid.shape[0]),
                    "median_hours": round(float(valid.median()), 3)
                    if not valid.empty
                    else pd.NA,
                    "mean_hours": round(float(valid.mean()), 3)
                    if not valid.empty
                    else pd.NA,
                    "p90_hours": round(float(valid.quantile(0.9)), 3)
                    if not valid.empty
                    else pd.NA,
                }
            )
    return pd.DataFrame(rows)


def build_cohort_summary(df: pd.DataFrame) -> pd.DataFrame:
    analysis = df[df["analysis_in_scope"]].copy()

    rows: list[dict[str, object]] = []
    for cohort, group in analysis.groupby("cohort_weekpart", dropna=False):
        rows.append(
            {
                "cohort": cohort,
                "ordered_tests": int(group.shape[0]),
                "completed_tests": int(group["is_completed"].sum()),
                "cancelled_tests": int(group["is_cancelled"].sum()),
                "cancellation_rate": round(float(group["is_cancelled"].mean()), 4),
                "median_hours_order_to_collect": round(
                    float(group["hours_order_to_collect"].dropna().median()), 3
                )
                if group["hours_order_to_collect"].notna().any()
                else pd.NA,
                "median_hours_collect_to_receipt": round(
                    float(group["hours_collect_to_receipt"].dropna().median()), 3
                )
                if group["hours_collect_to_receipt"].notna().any()
                else pd.NA,
                "median_hours_receipt_to_verified": round(
                    float(group["hours_receipt_to_verified"].dropna().median()), 3
                )
                if group["hours_receipt_to_verified"].notna().any()
                else pd.NA,
                "median_hours_order_to_verified": round(
                    float(group["hours_order_to_verified"].dropna().median()), 3
                )
                if group["hours_order_to_verified"].notna().any()
                else pd.NA,
            }
        )

    return pd.DataFrame(rows)


def write_markdown_summary(
    cohort_summary: pd.DataFrame, output_path: Path, analysis_df: pd.DataFrame
) -> None:
    weekday_row = cohort_summary[cohort_summary["cohort"] == "Weekday"]
    weekend_row = cohort_summary[cohort_summary["cohort"] == "Weekend"]

    lines = [
        "# Weekday vs Weekend Summary",
        "",
        f"- Ordered tests in 2025 scope: {int(analysis_df.shape[0]):,}",
        f"- Ordered tests with any non-2025 event timestamp: {int(analysis_df['has_any_non_2025_event'].sum()):,}",
        "",
    ]

    if not weekday_row.empty and not weekend_row.empty:
        weekday = weekday_row.iloc[0]
        weekend = weekend_row.iloc[0]
        cancel_delta = (
            float(weekend["cancellation_rate"]) - float(weekday["cancellation_rate"])
        ) * 100
        tat_delta = float(weekend["median_hours_order_to_verified"]) - float(
            weekday["median_hours_order_to_verified"]
        )

        lines.extend(
            [
                f"- Weekday cancellation rate: {weekday['cancellation_rate']:.2%}",
                f"- Weekend cancellation rate: {weekend['cancellation_rate']:.2%}",
                f"- Weekend minus weekday cancellation rate: {cancel_delta:.2f} percentage points",
                f"- Weekday median order-to-verified time: {weekday['median_hours_order_to_verified']:.2f} hours",
                f"- Weekend median order-to-verified time: {weekend['median_hours_order_to_verified']:.2f} hours",
                f"- Weekend minus weekday median order-to-verified time: {tat_delta:.2f} hours",
            ]
        )

    output_path.write_text("\n".join(lines) + "\n")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ordered_tests = build_ordered_test_frame(input_path)
    ordered_tests = add_datetime_and_duration_columns(ordered_tests)

    ordered_tests_path = output_dir / "ordered_test_metrics.parquet"
    cohort_summary_path = output_dir / "weekday_vs_weekend_summary.csv"
    stage_summary_path = output_dir / "weekday_vs_weekend_stage_summary.csv"
    markdown_summary_path = output_dir / "weekday_vs_weekend_summary.md"

    ordered_tests.to_parquet(ordered_tests_path, index=False)

    cohort_summary = build_cohort_summary(ordered_tests)
    stage_summary = build_stage_summary(ordered_tests)

    cohort_summary.to_csv(cohort_summary_path, index=False)
    stage_summary.to_csv(stage_summary_path, index=False)
    write_markdown_summary(
        cohort_summary,
        markdown_summary_path,
        ordered_tests[ordered_tests["analysis_in_scope"]].copy(),
    )

    print(f"Wrote {ordered_tests_path}")
    print(f"Wrote {cohort_summary_path}")
    print(f"Wrote {stage_summary_path}")
    print(f"Wrote {markdown_summary_path}")


if __name__ == "__main__":
    main()
