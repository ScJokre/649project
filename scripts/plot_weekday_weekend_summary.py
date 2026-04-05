#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


COLORS = {
    "Weekday": "#1f5aa6",
    "Weekend": "#d96c06",
}

STAGE_LABELS = {
    "order_to_collect": "Order -> Collect",
    "collect_to_receipt": "Collect -> Receipt",
    "receipt_to_verified": "Receipt -> Verified",
    "order_to_verified": "Order -> Verified",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a static weekday versus weekend comparison figure."
    )
    parser.add_argument(
        "--summary",
        default="output/data/weekday_vs_weekend_summary.csv",
        help="Path to the cohort summary CSV.",
    )
    parser.add_argument(
        "--stage-summary",
        default="output/data/weekday_vs_weekend_stage_summary.csv",
        help="Path to the stage summary CSV.",
    )
    parser.add_argument(
        "--output",
        default="output/figures/weekday_vs_weekend_overview.png",
        help="Path to the output PNG.",
    )
    return parser.parse_args()


def add_bar_labels(ax: plt.Axes, bars, fmt: str, suffix: str = "") -> None:
    for bar in bars:
        value = bar.get_width() if bar.get_width() else bar.get_height()
        if value is None:
            continue
        if hasattr(bar, "get_width") and bar.get_width() != 0:
            ax.text(
                bar.get_width() + 0.05,
                bar.get_y() + bar.get_height() / 2,
                f"{format(value, fmt)}{suffix}",
                va="center",
                ha="left",
                fontsize=9,
            )
        else:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.002,
                f"{format(value, fmt)}{suffix}",
                va="bottom",
                ha="center",
                fontsize=9,
            )


def main() -> None:
    args = parse_args()
    summary = pd.read_csv(args.summary)
    stage_summary = pd.read_csv(args.stage_summary)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    stage_summary["stage_label"] = stage_summary["stage"].map(STAGE_LABELS)
    stage_order = [
        "Order -> Collect",
        "Collect -> Receipt",
        "Receipt -> Verified",
        "Order -> Verified",
    ]
    stage_summary["stage_label"] = pd.Categorical(
        stage_summary["stage_label"], categories=stage_order, ordered=True
    )
    stage_summary = stage_summary.sort_values(["stage_label", "cohort"])

    fig = plt.figure(figsize=(13, 6.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.7, 1.0])
    ax_stage = fig.add_subplot(gs[0, 0])
    ax_cancel = fig.add_subplot(gs[0, 1])

    y_positions = list(range(len(stage_order)))
    bar_height = 0.35

    weekday_stage = (
        stage_summary[stage_summary["cohort"] == "Weekday"]
        .set_index("stage_label")
        .reindex(stage_order)
    )
    weekend_stage = (
        stage_summary[stage_summary["cohort"] == "Weekend"]
        .set_index("stage_label")
        .reindex(stage_order)
    )

    weekday_bars = ax_stage.barh(
        [y - bar_height / 2 for y in y_positions],
        weekday_stage["median_hours"],
        height=bar_height,
        color=COLORS["Weekday"],
        label="Weekday",
    )
    weekend_bars = ax_stage.barh(
        [y + bar_height / 2 for y in y_positions],
        weekend_stage["median_hours"],
        height=bar_height,
        color=COLORS["Weekend"],
        label="Weekend",
    )

    ax_stage.set_yticks(y_positions)
    ax_stage.set_yticklabels(stage_order)
    ax_stage.invert_yaxis()
    ax_stage.set_xlabel("Median hours")
    ax_stage.set_title("Stage Duration Comparison")
    ax_stage.grid(axis="x", linestyle="--", alpha=0.3)
    ax_stage.legend(frameon=False, loc="lower right")
    add_bar_labels(ax_stage, weekday_bars, ".2f", "h")
    add_bar_labels(ax_stage, weekend_bars, ".2f", "h")

    cancel_plot = summary.copy()
    cancel_plot["cancellation_pct"] = cancel_plot["cancellation_rate"] * 100
    cancel_plot = cancel_plot.set_index("cohort").reindex(["Weekday", "Weekend"])

    cancel_bars = ax_cancel.bar(
        cancel_plot.index,
        cancel_plot["cancellation_pct"],
        color=[COLORS[cohort] for cohort in cancel_plot.index],
        width=0.55,
    )
    ax_cancel.set_ylabel("Cancellation rate (%)")
    ax_cancel.set_title("Cancellation Likelihood")
    ax_cancel.set_ylim(0, max(cancel_plot["cancellation_pct"].max() * 1.35, 6))
    ax_cancel.grid(axis="y", linestyle="--", alpha=0.3)

    for bar, cohort in zip(cancel_bars, cancel_plot.index):
        value = cancel_plot.loc[cohort, "cancellation_pct"]
        n_value = int(cancel_plot.loc[cohort, "ordered_tests"])
        ax_cancel.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.08,
            f"{value:.2f}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )
        ax_cancel.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() / 2,
            f"n={n_value:,}",
            ha="center",
            va="center",
            fontsize=9,
            color="white",
            fontweight="bold",
        )

    weekday_tat = float(
        summary.loc[summary["cohort"] == "Weekday", "median_hours_order_to_verified"].iloc[0]
    )
    weekend_tat = float(
        summary.loc[summary["cohort"] == "Weekend", "median_hours_order_to_verified"].iloc[0]
    )
    cancel_delta = float(
        cancel_plot.loc["Weekend", "cancellation_pct"]
        - cancel_plot.loc["Weekday", "cancellation_pct"]
    )
    tat_delta = weekend_tat - weekday_tat

    fig.suptitle("Weekday vs Weekend Ordered Test Comparison", fontsize=15, y=0.98)
    fig.text(
        0.58,
        0.08,
        (
            f"Median order -> verified: Weekday {weekday_tat:.2f}h, "
            f"Weekend {weekend_tat:.2f}h\n"
            f"Cancellation delta: Weekend {cancel_delta:+.2f} percentage points | "
            f"TAT delta: Weekend {tat_delta:+.2f}h"
        ),
        fontsize=10,
    )

    fig.tight_layout(rect=[0, 0.12, 1, 0.95])
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
