#!/usr/bin/env python3
from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image, ImageOps


WEEKDAY_COLOR = "#2F5D8C"
WEEKEND_COLOR = "#C96B23"
INK = "#1B1B1B"
NOTE = "#5A5A5A"
PAPER = "#FFFDF7"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate three project sketch PNGs.")
    parser.add_argument(
        "--output-dir",
        default="output/sketches",
        help="Directory where the sketch PNGs should be written.",
    )
    return parser.parse_args()


def setup_figure():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "path.sketch": (1, 120, 2),
            "lines.solid_capstyle": "round",
            "axes.edgecolor": INK,
            "text.color": INK,
        }
    )
    fig, ax = plt.subplots(figsize=(12, 8), dpi=180)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, title, body=None, color=INK, lw=2):
    rect = Rectangle((x, y), w, h, fill=False, linewidth=lw, edgecolor=color)
    ax.add_patch(rect)
    ax.text(x + 1.6, y + h - 3, title, fontsize=11, fontweight="bold", va="top")
    if body:
        ax.text(x + 1.6, y + h - 8, body, fontsize=8.8, va="top", color=NOTE)


def note(ax, x, y, text):
    wrapped = textwrap.fill(text, width=48)
    ax.text(
        x,
        y,
        wrapped,
        fontsize=8.0,
        color=NOTE,
        va="top",
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "#FFF8E6", "edgecolor": "#D8C9A6"},
    )


def arrow_label(ax, x1, y1, x2, y2, text, color=NOTE):
    ax.annotate(
        text,
        xy=(x2, y2),
        xytext=(x1, y1),
        fontsize=8.2,
        color=color,
        arrowprops={"arrowstyle": "->", "color": color, "linewidth": 1.2},
    )


def save(fig, path: Path):
    fig.tight_layout(pad=0.8)
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def sketch_1_dashboard(output_path: Path):
    fig, ax = setup_figure()
    ax.text(3, 96, "Sketch 1  Dashboard Overview", fontsize=18, fontweight="bold")
    ax.text(
        3,
        91.5,
        "Goal: show the full dashboard structure and how the views work together.",
        fontsize=10,
        color=NOTE,
    )

    box(ax, 3, 15, 20, 68, "Filters")
    box(ax, 25, 48, 47, 35, "Average Journey Timeline")
    box(ax, 74, 48, 23, 35, "A/B KPI Summary")
    box(ax, 25, 15, 47, 29, "Stage Duration Comparison")
    box(ax, 74, 15, 23, 29, "Cancellation Likelihood")
    box(ax, 3, 5, 94, 7, "Details on Demand")

    ax.text(6, 73.5, "cohort", fontsize=8.5, color=NOTE)
    ax.text(6, 70.5, "- weekday / weekend", fontsize=9)
    for y, label in zip([64, 57, 50, 43], ["test code", "event street", "performing dept", "date range"]):
        ax.text(7.2, y, f"- {label}", fontsize=9)

    ax.text(27.5, 73.5, "median elapsed hours since order", fontsize=8.4, color=NOTE)
    ax.text(27.5, 69.8, "ordered -> collected -> receipt -> verified", fontsize=8.8, color=NOTE)

    timeline_y = [71, 60]
    labels = ["Weekday", "Weekend"]
    xs = [[33, 40, 50, 63], [33, 44, 51, 66]]
    colors = [WEEKDAY_COLOR, WEEKEND_COLOR]
    for y, lab, row_xs, color in zip(timeline_y, labels, xs, colors):
        ax.text(27.5, y, lab, fontsize=9.5, fontweight="bold", color=color, va="center")
        ax.plot(row_xs, [y] * len(row_xs), color=color, linewidth=2.2)
        ax.scatter(row_xs, [y] * len(row_xs), s=28, color=color, zorder=3)
    for x, lab in zip(xs[0], ["ordered", "collected", "receipt", "verified"]):
        ax.text(x - 1.5, 53.5, lab, fontsize=7.6, rotation=10)

    ax.text(77, 73, "A: Weekday", fontsize=9.2, fontweight="bold", color=WEEKDAY_COLOR)
    ax.text(77, 68, "B: Weekend", fontsize=9.2, fontweight="bold", color=WEEKEND_COLOR)
    ax.text(77, 61.5, "Median TAT", fontsize=8.8)
    ax.text(95, 61.5, "1.75h / 1.10h", fontsize=8.8, ha="right")
    ax.text(77, 56.5, "Cancel rate", fontsize=8.8)
    ax.text(95, 56.5, "4.28% / 4.52%", fontsize=8.8, ha="right")
    ax.text(77, 51.5, "Delta", fontsize=8.8)
    ax.text(95, 51.5, "weekend -0.65h", fontsize=8.8, ha="right")

    stage_names = ["Order->Collect", "Collect->Receipt", "Receipt->Verified"]
    centers = [36, 29.5, 23]
    weekday_vals = [8.5, 18, 24]
    weekend_vals = [15, 10.5, 19]
    for y, stage, wv, ev in zip(centers, stage_names, weekday_vals, weekend_vals):
        ax.text(27.5, y + 1.3, stage, fontsize=8.4)
        ax.add_patch(Rectangle((45.5, y), wv, 1.7, color=WEEKDAY_COLOR, alpha=0.9))
        ax.add_patch(Rectangle((45.5, y - 2.6), ev, 1.7, color=WEEKEND_COLOR, alpha=0.9))

    ax.text(77, 35, "weekday % vs weekend %", fontsize=8.4, color=NOTE)
    ax.add_patch(Rectangle((79, 23.5), 7.4, 10.5, color=WEEKDAY_COLOR, alpha=0.92))
    ax.add_patch(Rectangle((88.5, 23.5), 7.4, 11.1, color=WEEKEND_COLOR, alpha=0.92))
    ax.text(82.7, 21.2, "Weekday", fontsize=7.8, ha="center")
    ax.text(92.2, 21.2, "Weekend", fontsize=7.8, ha="center")

    arrow_label(ax, 12, 86, 19.5, 76, "interactive filters")
    arrow_label(ax, 57, 88, 51, 73.5, "main answer lives here")
    arrow_label(ax, 94, 85, 90, 65, "fast summary")
    arrow_label(ax, 60, 8.5, 50, 10.5, "details on demand")

    note(ax, 5, 10.5, "Use color for cohort. Use x-position and bar length for time.")
    note(ax, 34, 10.5, "Main timeline is centered because the client asked for an inspectable average timeline.")
    note(ax, 71, 10.5, "Cancellation is kept separate from timing so risk is not confused with duration.")
    ax.text(5, 2.8, "selected cohort notes, subset description, caveats", fontsize=8.3, color=NOTE)

    save(fig, output_path)


def sketch_2_timeline(output_path: Path):
    fig, ax = setup_figure()
    ax.text(3, 96, "Sketch 2  Average Journey Timeline Option", fontsize=18, fontweight="bold")
    ax.text(
        3,
        91.5,
        "Goal: test the main chart form for showing the average specimen journey over time.",
        fontsize=10,
        color=NOTE,
    )

    ax.plot([15, 91], [78, 78], color=INK, linewidth=2)
    for x, label in zip([20, 35, 50, 65, 80, 90], ["0h", "0.5h", "1h", "2h", "4h", "6h"]):
        ax.plot([x, x], [77, 79], color=INK, linewidth=1.5)
        ax.text(x, 81, label, fontsize=8.5, ha="center")
    ax.text(53, 85, "Elapsed Time Since Order", fontsize=11, ha="center", fontweight="bold")

    weekday_x = [20, 31, 41, 60]
    weekend_x = [20, 38, 45, 56]
    y_weekday = 58
    y_weekend = 38

    for xs, y, color, lab in [
        (weekday_x, y_weekday, WEEKDAY_COLOR, "Weekday"),
        (weekend_x, y_weekend, WEEKEND_COLOR, "Weekend"),
    ]:
        ax.text(9, y, lab, fontsize=12, fontweight="bold", color=color, va="center")
        ax.plot(xs, [y] * len(xs), color=color, linewidth=2.6)
        ax.scatter(xs, [y] * len(xs), s=36, color=color, zorder=3)

    for x, lab in zip(weekday_x, ["ordered", "collected", "receipt", "verified"]):
        ax.text(x, y_weekday - 7.5, lab, fontsize=8.5, ha="center")
    for x, lab in zip(weekend_x, ["ordered", "collected", "receipt", "verified"]):
        ax.text(x, y_weekend - 7.5, lab, fontsize=8.5, ha="center")

    ax.plot([31, 31], [54, 62], color=WEEKDAY_COLOR, linewidth=1.2, alpha=0.5)
    ax.plot([41, 41], [54, 62], color=WEEKDAY_COLOR, linewidth=1.2, alpha=0.5)
    ax.plot([38, 38], [34, 42], color=WEEKEND_COLOR, linewidth=1.2, alpha=0.5)
    ax.plot([45, 45], [34, 42], color=WEEKEND_COLOR, linewidth=1.2, alpha=0.5)
    ax.text(69, 62, "optional whiskers for spread", fontsize=8.5, color=NOTE)

    arrow_label(ax, 76, 48, 38, 38, "longer order -> collect gap")
    arrow_label(ax, 77, 31, 56, 38, "shorter total time here")
    arrow_label(ax, 64, 87, 62, 78, "shared time axis")

    note(ax, 5, 20, "A milestone timeline preserves sequence better than stacked bars.")
    note(ax, 5, 11.5, "Alternative considered: stacked stage bars. Not chosen as the main view because the event sequence is less explicit.")
    note(ax, 55, 20, "Distance between points shows where the delay occurs.")
    note(ax, 55, 11.5, "This directly answers the client's request for a graphic timeline.")

    save(fig, output_path)


def sketch_3_ab(output_path: Path):
    fig, ax = setup_figure()
    ax.text(3, 96, "Sketch 3  A/B Comparison And Event Likelihood", fontsize=18, fontweight="bold")
    ax.text(
        3,
        91.5,
        "Goal: show direct cohort comparison for stage duration and cancellation risk.",
        fontsize=10,
        color=NOTE,
    )

    box(ax, 4, 43, 92, 40, "Stage Duration Comparison")
    ax.text(6, 74.5, "Grouped bars for three process stages", fontsize=8.8, color=NOTE)
    stages = ["Order -> Collect", "Collect -> Receipt", "Receipt -> Verified"]
    y_rows = [72, 61, 50]
    weekday_vals = [14, 24, 30]
    weekend_vals = [22, 15, 25]

    for y, stage, wv, ev in zip(y_rows, stages, weekday_vals, weekend_vals):
        ax.text(8, y + 1, stage, fontsize=9.2, va="center")
        ax.add_patch(Rectangle((39, y + 1.2), wv, 2.2, color=WEEKDAY_COLOR, alpha=0.95))
        ax.add_patch(Rectangle((39, y - 2.4), ev, 2.2, color=WEEKEND_COLOR, alpha=0.95))
        ax.text(36.5, y + 2.2, "Wkdy", fontsize=7.8, ha="right", color=WEEKDAY_COLOR)
        ax.text(36.5, y - 1.4, "Wknd", fontsize=7.8, ha="right", color=WEEKEND_COLOR)

    box(ax, 4, 12, 92, 24, "Cancellation Likelihood")
    ax.text(6, 28.3, "Separate chart so time and risk are not mixed", fontsize=8.8, color=NOTE)
    ax.add_patch(Rectangle((20, 16), 18, 11.3, color=WEEKDAY_COLOR, alpha=0.92))
    ax.add_patch(Rectangle((48, 16), 18, 12.0, color=WEEKEND_COLOR, alpha=0.92))
    ax.text(29, 29.5, "4.28%", fontsize=12, color=INK, ha="center", fontweight="bold")
    ax.text(57, 30.2, "4.52%", fontsize=12, color=INK, ha="center", fontweight="bold")
    ax.text(29, 13, "Weekday", fontsize=9, ha="center")
    ax.text(57, 13, "Weekend", fontsize=9, ha="center")

    ax.text(72, 25.5, "delta:", fontsize=10, fontweight="bold")
    ax.text(79, 25.5, "weekend +0.24 pp", fontsize=10)
    ax.text(72, 20.5, "takeaway:", fontsize=10, fontweight="bold")
    ax.text(79, 20.5, "higher cancel risk, shorter total TAT", fontsize=10)

    arrow_label(ax, 88, 78, 68, 73, "grouped comparison")
    arrow_label(ax, 88, 33, 60, 24, "event probability")
    arrow_label(ax, 16, 40, 19, 28, "risk stays separate\nfrom time")

    note(ax, 5, 10, "Grouped bars make it easy to see which stage differs most.")
    note(ax, 42, 10, "Text deltas help non-technical stakeholders read the takeaway quickly.")
    note(ax, 71, 10, "Use row = stage, bar length = median duration, color = cohort.")

    save(fig, output_path)


def build_contact_sheet(image_paths: list[Path], output_path: Path):
    images = [Image.open(path).convert("RGB") for path in image_paths]
    bordered = [ImageOps.expand(img, border=12, fill="white") for img in images]
    width = max(img.width for img in bordered)
    gap = 20
    total_height = sum(img.height for img in bordered) + gap * (len(bordered) - 1)
    sheet = Image.new("RGB", (width, total_height), color="white")

    y = 0
    for img in bordered:
        x = (width - img.width) // 2
        sheet.paste(img, (x, y))
        y += img.height + gap

    sheet.save(output_path)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sketch1 = output_dir / "sketch_1_dashboard_overview.png"
    sketch2 = output_dir / "sketch_2_average_journey_timeline.png"
    sketch3 = output_dir / "sketch_3_ab_comparison_and_risk.png"
    contact = output_dir / "sketches_contact_sheet.png"

    sketch_1_dashboard(sketch1)
    sketch_2_timeline(sketch2)
    sketch_3_ab(sketch3)
    build_contact_sheet([sketch1, sketch2, sketch3], contact)

    print(f"Wrote {sketch1}")
    print(f"Wrote {sketch2}")
    print(f"Wrote {sketch3}")
    print(f"Wrote {contact}")


if __name__ == "__main__":
    main()
