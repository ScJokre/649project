from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Specimen Journey Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)


DATA_PATH = Path("output/data/ordered_test_metrics.parquet")

COHORT_COLORS = {
    "A": "#0E5A8A",
    "B": "#D97706",
}

DISPLAY_FIELDS = {
    "Weekpart": "cohort_weekpart",
    "Weekday Name": "ordered_weekday_name",
    "Event Street": "event_street",
    "Performing Department": "test_performing_dept",
    "Test Code": "test_code",
}

HOTSPOT_FIELDS = {
    "Test Code": "test_code",
    "Event Street": "event_street",
    "Performing Department": "test_performing_dept",
    "Weekday Name": "ordered_weekday_name",
}

MILESTONE_SPECS = [
    ("Ordered", "test_ordered_dt", "test_ordered_dt"),
    ("Collected", "test_collected_dt", "test_ordered_dt"),
    ("Receipt", "test_receipt_dt", "test_ordered_dt"),
    ("Verified", "final_verified_dt", "test_ordered_dt"),
]

STAGE_SPECS = [
    ("Order -> Collect", "hours_order_to_collect"),
    ("Collect -> Receipt", "hours_collect_to_receipt"),
    ("Receipt -> Verified", "hours_receipt_to_verified"),
    ("Order -> Verified", "hours_order_to_verified"),
]

RISK_EVENT_OPTIONS = {
    "Cancellation": {"type": "boolean", "column": "is_cancelled"},
    "Long Order -> Collect": {"type": "threshold", "column": "hours_order_to_collect"},
    "Long Collect -> Receipt": {"type": "threshold", "column": "hours_collect_to_receipt"},
    "Long Receipt -> Verified": {"type": "threshold", "column": "hours_receipt_to_verified"},
    "Long Order -> Verified": {"type": "threshold", "column": "hours_order_to_verified"},
}


@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df = df[df["analysis_in_scope"]].copy()
    df["ordered_date"] = pd.to_datetime(df["test_ordered_dt"], utc=True, errors="coerce")
    return df


def apply_base_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()

    st.sidebar.markdown("## Filter Scope")
    exclude_cross_year = st.sidebar.checkbox(
        "Exclude cross-year anomalies",
        value=True,
        help="Removes the small number of 2025 orders that contain non-2025 event timestamps.",
    )
    if exclude_cross_year:
        filtered = filtered[~filtered["has_any_non_2025_event"]]

    test_codes = st.sidebar.multiselect(
        "Test code",
        options=sorted(filtered["test_code"].dropna().unique().tolist()),
        default=[],
    )
    if test_codes:
        filtered = filtered[filtered["test_code"].isin(test_codes)]

    streets = st.sidebar.multiselect(
        "Event street",
        options=sorted(filtered["event_street"].dropna().unique().tolist()),
        default=[],
    )
    if streets:
        filtered = filtered[filtered["event_street"].isin(streets)]

    departments = st.sidebar.multiselect(
        "Performing department",
        options=sorted(filtered["test_performing_dept"].dropna().unique().tolist()),
        default=[],
    )
    if departments:
        filtered = filtered[filtered["test_performing_dept"].isin(departments)]

    completed_only = st.sidebar.checkbox(
        "Completed tests only",
        value=False,
        help="Keeps only orders that reached final verification.",
    )
    if completed_only:
        filtered = filtered[filtered["is_completed"]]

    return filtered


def comparison_controls(df: pd.DataFrame) -> tuple[pd.DataFrame, str, str, str]:
    st.sidebar.markdown("## A/B Comparison")
    display_name = st.sidebar.selectbox(
        "Comparison dimension",
        list(DISPLAY_FIELDS.keys()),
        index=0,
    )
    comparison_field = DISPLAY_FIELDS[display_name]
    available_values = (
        df[comparison_field]
        .dropna()
        .astype(str)
        .value_counts()
        .index
        .tolist()
    )

    if len(available_values) < 2:
        return df.iloc[0:0], display_name, "", ""

    default_a = available_values[0]
    default_b = available_values[1]
    if comparison_field == "cohort_weekpart":
        default_a = "Weekday" if "Weekday" in available_values else available_values[0]
        default_b = "Weekend" if "Weekend" in available_values else available_values[1]

    cohort_a = st.sidebar.selectbox(
        "Cohort A",
        available_values,
        index=available_values.index(default_a),
    )
    remaining = [value for value in available_values if value != cohort_a]
    cohort_b = st.sidebar.selectbox(
        "Cohort B",
        remaining,
        index=remaining.index(default_b) if default_b in remaining else 0,
    )

    compared = df[df[comparison_field].astype(str).isin([cohort_a, cohort_b])].copy()
    compared["comparison_label"] = compared[comparison_field].astype(str).map(
        {cohort_a: f"A: {cohort_a}", cohort_b: f"B: {cohort_b}"}
    )
    return compared, display_name, cohort_a, cohort_b


def risk_event_controls() -> str:
    st.sidebar.markdown("## Risk Event")
    return st.sidebar.selectbox(
        "Event likelihood metric",
        list(RISK_EVENT_OPTIONS.keys()),
        index=0,
        help="Choose which event definition to compare across cohorts.",
    )


def event_thresholds(df: pd.DataFrame) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    for spec in RISK_EVENT_OPTIONS.values():
        if spec["type"] != "threshold":
            continue
        series = df[spec["column"]].dropna()
        series = series[series >= 0]
        thresholds[spec["column"]] = float(series.quantile(0.9)) if not series.empty else float("nan")
    return thresholds


def apply_risk_event(
    df: pd.DataFrame, event_name: str, thresholds: dict[str, float]
) -> tuple[pd.DataFrame, str]:
    spec = RISK_EVENT_OPTIONS[event_name]
    out = df.copy()

    if spec["type"] == "boolean":
        out["selected_event_flag"] = out[spec["column"]].fillna(False).astype(bool)
        description = "`cancellation_dt`"
    else:
        threshold = thresholds.get(spec["column"], float("nan"))
        out["selected_event_flag"] = out[spec["column"]].ge(threshold).fillna(False)
        description = f"{spec['column']} >= current filtered p90 ({threshold:.2f}h)"

    return out, description


def summarize_group(group_df: pd.DataFrame) -> dict[str, float | int]:
    return {
        "n": int(group_df.shape[0]),
        "completed": int(group_df["is_completed"].sum()),
        "event_rate": float(group_df["selected_event_flag"].mean()) if len(group_df) else 0.0,
        "cancel_rate": float(group_df["is_cancelled"].mean()) if len(group_df) else 0.0,
        "median_tat": float(group_df["hours_order_to_verified"].dropna().median())
        if group_df["hours_order_to_verified"].notna().any()
        else float("nan"),
    }


def format_hours(value: float) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{value:.2f} h"


def format_pct_pp(value: float) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{value:+.2f} pp"


def build_timeline_frame(df: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for milestone, event_col, start_col in MILESTONE_SPECS:
        elapsed = (df[event_col] - df[start_col]).dt.total_seconds() / 3600.0
        tmp = pd.DataFrame(
            {
                "comparison_label": df["comparison_label"],
                "milestone": milestone,
                "elapsed_hours": elapsed,
            }
        ).dropna()
        tmp = tmp[tmp["elapsed_hours"] >= 0]
        if tmp.empty:
            continue
        frames.append(
            tmp.groupby(["comparison_label", "milestone"], as_index=False)["elapsed_hours"].median()
        )

    if not frames:
        return pd.DataFrame(columns=["comparison_label", "milestone", "elapsed_hours"])

    out = pd.concat(frames, ignore_index=True)
    out["milestone"] = pd.Categorical(
        out["milestone"],
        categories=[item[0] for item in MILESTONE_SPECS],
        ordered=True,
    )
    return out.sort_values(["comparison_label", "milestone"])


def build_stage_frame(df: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for stage_label, column in STAGE_SPECS:
        tmp = df[["comparison_label", column]].dropna().rename(columns={column: "hours"})
        tmp = tmp[tmp["hours"] >= 0]
        if tmp.empty:
            continue
        summary = tmp.groupby("comparison_label", as_index=False)["hours"].median()
        summary["stage"] = stage_label
        frames.append(summary)

    if not frames:
        return pd.DataFrame(columns=["comparison_label", "hours", "stage"])

    out = pd.concat(frames, ignore_index=True)
    out["stage"] = pd.Categorical(
        out["stage"],
        categories=[item[0] for item in STAGE_SPECS],
        ordered=True,
    )
    return out.sort_values(["stage", "comparison_label"])


def stage_delta_summary(stage_df: pd.DataFrame, cohort_a: str, cohort_b: str) -> dict[str, object] | None:
    if stage_df.empty:
        return None

    focus = stage_df[stage_df["stage"] != "Order -> Verified"].copy()
    if focus.empty:
        focus = stage_df.copy()

    pivot = focus.pivot(index="stage", columns="comparison_label", values="hours").reset_index()
    label_a = f"A: {cohort_a}"
    label_b = f"B: {cohort_b}"
    if label_a not in pivot.columns or label_b not in pivot.columns:
        return None

    pivot["delta_hours"] = pivot[label_b] - pivot[label_a]
    pivot["abs_delta"] = pivot["delta_hours"].abs()
    top = pivot.sort_values("abs_delta", ascending=False).iloc[0]
    return {"stage": str(top["stage"]), "delta_hours": float(top["delta_hours"])}


def build_hotspot_frame(
    df: pd.DataFrame, dimension: str, cohort_a: str, cohort_b: str, min_size: int
) -> pd.DataFrame:
    label_a = f"A: {cohort_a}"
    label_b = f"B: {cohort_b}"

    base = df[[dimension, "comparison_label", "hours_order_to_verified", "selected_event_flag"]].dropna(
        subset=[dimension]
    )
    if base.empty:
        return pd.DataFrame()

    grouped = (
        base.groupby([dimension, "comparison_label"], as_index=False)
        .agg(
            n=("comparison_label", "size"),
            median_tat=("hours_order_to_verified", "median"),
            event_rate=("selected_event_flag", "mean"),
        )
    )

    wide = grouped.pivot(index=dimension, columns="comparison_label")
    wide.columns = [f"{metric}_{label}" for metric, label in wide.columns]
    wide = wide.reset_index()

    required = [
        f"n_{label_a}",
        f"n_{label_b}",
        f"median_tat_{label_a}",
        f"median_tat_{label_b}",
        f"event_rate_{label_a}",
        f"event_rate_{label_b}",
    ]
    for col in required:
        if col not in wide.columns:
            wide[col] = pd.NA

    wide = wide.dropna(subset=[f"n_{label_a}", f"n_{label_b}"]).copy()
    wide = wide[
        (wide[f"n_{label_a}"] >= min_size) & (wide[f"n_{label_b}"] >= min_size)
    ].copy()
    if wide.empty:
        return wide

    wide["tat_delta_hours"] = wide[f"median_tat_{label_b}"] - wide[f"median_tat_{label_a}"]
    wide["event_delta_pp"] = (
        wide[f"event_rate_{label_b}"] - wide[f"event_rate_{label_a}"]
    ) * 100
    wide["abs_tat_delta"] = wide["tat_delta_hours"].abs()
    wide["abs_event_delta"] = wide["event_delta_pp"].abs()
    return wide.sort_values("abs_tat_delta", ascending=False)


def build_story(
    summary_a: dict[str, float | int],
    summary_b: dict[str, float | int],
    stage_summary: dict[str, object] | None,
    event_name: str,
) -> list[str]:
    story: list[str] = []
    tat_delta = summary_b["median_tat"] - summary_a["median_tat"]
    event_delta = (summary_b["event_rate"] - summary_a["event_rate"]) * 100

    if not math.isnan(tat_delta):
        direction = "faster" if tat_delta < 0 else "slower"
        story.append(
            f"Cohort B is {abs(tat_delta):.2f} hours {direction} than Cohort A on median order-to-verified turnaround time."
        )
    story.append(
        f"Cohort B changes {event_name.lower()} likelihood by {event_delta:+.2f} percentage points relative to Cohort A."
    )
    if stage_summary is not None:
        stage_direction = "slower" if stage_summary["delta_hours"] > 0 else "faster"
        story.append(
            f"The largest stage gap appears in {stage_summary['stage']}, where Cohort B is {abs(stage_summary['delta_hours']):.2f} hours {stage_direction}."
        )
    return story


def metric_card(column, title: str, value: str, help_text: str) -> None:
    with column:
        st.markdown(
            f"""
            <div style="border:1px solid #E7E1D8;border-radius:14px;padding:14px 16px;background:#FFFDF8;">
                <div style="font-size:0.88rem;color:#6E6355;">{title}</div>
                <div style="font-size:1.7rem;font-weight:700;color:#1D1D1D;">{value}</div>
                <div style="font-size:0.78rem;color:#7A736C;">{help_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_dashboard(
    df: pd.DataFrame,
    comparison_name: str,
    cohort_a: str,
    cohort_b: str,
    event_name: str,
    event_description: str,
) -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top left, #F4EEDF 0%, rgba(244,238,223,0.75) 22%, rgba(255,255,255,0) 55%),
                    radial-gradient(circle at bottom right, #E8F0F1 0%, rgba(232,240,241,0.72) 18%, rgba(255,255,255,0) 48%),
                    linear-gradient(180deg, #FFFCF7 0%, #F7F0E3 100%);
                font-family: "Avenir Next", "Trebuchet MS", sans-serif;
            }
            .hero {
                border: 1px solid #E6DECF;
                border-radius: 20px;
                background: linear-gradient(135deg, rgba(255,248,236,0.95), rgba(248,251,252,0.88));
                padding: 22px 24px;
                margin-bottom: 14px;
                box-shadow: 0 10px 30px rgba(76, 63, 46, 0.05);
            }
            .hero-title {
                font-size: 2.1rem;
                line-height: 1.05;
                font-weight: 800;
                margin-bottom: 6px;
                color: #1F2421;
            }
            .hero-subtitle {
                font-size: 1rem;
                color: #635A4E;
                max-width: 68rem;
            }
            .story-box {
                border: 1px solid #E8DDCA;
                border-radius: 16px;
                padding: 12px 16px;
                background: rgba(255, 252, 246, 0.96);
                margin-top: 10px;
            }
            .story-label {
                font-size: 0.82rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #7F725F;
                margin-bottom: 4px;
            }
            .story-line {
                font-size: 0.98rem;
                color: #2C2B29;
                margin: 0.2rem 0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if df.empty or not cohort_a or not cohort_b:
        st.error("The current filter and comparison settings do not leave two cohorts to compare.")
        return

    group_a = df[df["comparison_label"] == f"A: {cohort_a}"].copy()
    group_b = df[df["comparison_label"] == f"B: {cohort_b}"].copy()
    if group_a.empty or group_b.empty:
        st.error("One of the selected cohorts has no rows after filtering. Adjust the controls in the sidebar.")
        return

    summary_a = summarize_group(group_a)
    summary_b = summarize_group(group_b)
    stage_df = build_stage_frame(df)
    stage_summary = stage_delta_summary(stage_df, cohort_a, cohort_b)
    story_lines = build_story(summary_a, summary_b, stage_summary, event_name)

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-title">Specimen Journey Comparison Dashboard</div>
            <div class="hero-subtitle">
                Compare average specimen timelines, bottleneck stages, and event likelihood across mutually exclusive cohorts.
                The current lens is <strong>{comparison_name}</strong>, with <strong>A = {cohort_a}</strong> and <strong>B = {cohort_b}</strong>.
                Current event definition: <strong>{event_name}</strong> ({event_description}).
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_cols = st.columns(4)
    metric_card(top_cols[0], "Cohort A sample", f"{summary_a['n']:,}", "ordered tests after filters")
    metric_card(top_cols[1], "Cohort B sample", f"{summary_b['n']:,}", "ordered tests after filters")
    metric_card(
        top_cols[2],
        f"{event_name} delta",
        f"{(summary_b['event_rate'] - summary_a['event_rate']) * 100:+.2f} pp",
        f"B minus A {event_name.lower()} rate",
    )
    metric_card(
        top_cols[3],
        "Median TAT delta",
        f"{summary_b['median_tat'] - summary_a['median_tat']:+.2f} h",
        "B minus A order-to-verified median",
    )

    story_html = "".join(f'<div class="story-line">- {line}</div>' for line in story_lines)
    st.markdown(
        f"""
        <div class="story-box">
            <div class="story-label">Current Read</div>
            {story_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    overview_tab, hotspots_tab, details_tab = st.tabs(["Overview", "Hotspots", "Details & Method"])

    with overview_tab:
        left, right = st.columns([1.8, 1.1])

        with left:
            st.markdown("#### Average Journey Timeline")
            timeline_df = build_timeline_frame(df)
            if timeline_df.empty:
                st.info("Not enough event coverage to draw the timeline for the current selection.")
            else:
                fig = px.line(
                    timeline_df,
                    x="elapsed_hours",
                    y="milestone",
                    color="comparison_label",
                    markers=True,
                    category_orders={"milestone": [item[0] for item in MILESTONE_SPECS]},
                    color_discrete_map={
                        f"A: {cohort_a}": COHORT_COLORS["A"],
                        f"B: {cohort_b}": COHORT_COLORS["B"],
                    },
                )
                fig.update_layout(
                    height=390,
                    xaxis_title="Median elapsed hours since order",
                    yaxis_title="Milestone",
                    legend_title="Cohort",
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(255,255,255,0.82)",
                )
                fig.update_yaxes(autorange="reversed")

                verified = timeline_df[timeline_df["milestone"] == "Verified"].copy()
                if verified.shape[0] == 2:
                    delta = verified["elapsed_hours"].iloc[1] - verified["elapsed_hours"].iloc[0]
                    fig.add_annotation(
                        x=verified["elapsed_hours"].max(),
                        y="Verified",
                        text=f"delta {delta:+.2f}h",
                        showarrow=True,
                        arrowhead=1,
                        ay=-38,
                        bgcolor="rgba(255,250,240,0.92)",
                    )

                st.plotly_chart(fig, use_container_width=True)
                st.caption(
                    "Each point shows the median arrival time for a milestone, relative to the ordered timestamp."
                )

        with right:
            st.markdown("#### A/B Snapshot")
            snapshot = pd.DataFrame(
                [
                    {
                        "cohort": f"A: {cohort_a}",
                        "ordered_tests": summary_a["n"],
                        "completed_tests": summary_a["completed"],
                        f"{event_name}_rate": summary_a["event_rate"],
                        "median_order_to_verified_hours": summary_a["median_tat"],
                    },
                    {
                        "cohort": f"B: {cohort_b}",
                        "ordered_tests": summary_b["n"],
                        "completed_tests": summary_b["completed"],
                        f"{event_name}_rate": summary_b["event_rate"],
                        "median_order_to_verified_hours": summary_b["median_tat"],
                    },
                ]
            )
            st.dataframe(
                snapshot.style.format(
                    {
                        "ordered_tests": "{:,.0f}",
                        "completed_tests": "{:,.0f}",
                        f"{event_name}_rate": "{:.2%}",
                        "median_order_to_verified_hours": "{:.2f}",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("#### Interpretation Hints")
            st.markdown(
                f"""
                - Largest current stage gap: **{stage_summary['stage'] if stage_summary else 'n/a'}**
                - Cohort A median TAT: **{format_hours(summary_a['median_tat'])}**
                - Cohort B median TAT: **{format_hours(summary_b['median_tat'])}**
                - {event_name} delta: **{format_pct_pp((summary_b['event_rate'] - summary_a['event_rate']) * 100)}**
                """
            )

        lower_left, lower_right = st.columns([1.35, 1.0])

        with lower_left:
            st.markdown("#### Stage Duration Comparison")
            if stage_df.empty:
                st.info("Not enough stage duration coverage to compare this selection.")
            else:
                fig = px.bar(
                    stage_df,
                    x="hours",
                    y="stage",
                    color="comparison_label",
                    barmode="group",
                    orientation="h",
                    color_discrete_map={
                        f"A: {cohort_a}": COHORT_COLORS["A"],
                        f"B: {cohort_b}": COHORT_COLORS["B"],
                    },
                )
                fig.update_layout(
                    height=360,
                    xaxis_title="Median hours",
                    yaxis_title="Stage",
                    legend_title="Cohort",
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(255,255,255,0.82)",
                )
                if stage_summary is not None:
                    fig.add_annotation(
                        x=float(stage_df["hours"].max()),
                        y=stage_summary["stage"],
                        text=f"largest gap {stage_summary['delta_hours']:+.2f}h",
                        showarrow=False,
                        xanchor="right",
                        bgcolor="rgba(255,250,240,0.92)",
                    )
                st.plotly_chart(fig, use_container_width=True)

        with lower_right:
            st.markdown(f"#### Event Likelihood: {event_name}")
            likelihood_df = pd.DataFrame(
                {
                    "cohort": [f"A: {cohort_a}", f"B: {cohort_b}"],
                    "rate": [summary_a["event_rate"], summary_b["event_rate"]],
                }
            )
            fig = px.bar(
                likelihood_df,
                x="cohort",
                y="rate",
                color="cohort",
                text=likelihood_df["rate"].map(lambda x: f"{x:.2%}"),
                color_discrete_map={
                    f"A: {cohort_a}": COHORT_COLORS["A"],
                    f"B: {cohort_b}": COHORT_COLORS["B"],
                },
            )
            fig.update_layout(
                height=360,
                yaxis_title=f"{event_name} rate",
                xaxis_title="",
                showlegend=False,
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.82)",
            )
            fig.update_yaxes(tickformat=".0%")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"Current event definition: {event_description}.")

    with hotspots_tab:
        st.markdown("#### Where Are The Biggest Gaps?")
        controls = st.columns([1.1, 0.9])
        with controls[0]:
            hotspot_name = st.selectbox("Hotspot dimension", list(HOTSPOT_FIELDS.keys()))
        with controls[1]:
            min_size = st.slider("Minimum sample per cohort", min_value=10, max_value=200, value=30, step=10)

        hotspot_field = HOTSPOT_FIELDS[hotspot_name]
        hotspot_df = build_hotspot_frame(df, hotspot_field, cohort_a, cohort_b, min_size)
        if hotspot_df.empty:
            st.info("No categories satisfy the current hotspot settings. Try lowering the minimum sample size or broadening the filters.")
        else:
            top_tat = hotspot_df.nlargest(12, "abs_tat_delta").copy()
            top_event = hotspot_df.nlargest(12, "abs_event_delta").copy()

            row1, row2 = st.columns(2)
            with row1:
                st.markdown("##### Largest Turnaround-Time Gaps")
                fig = px.bar(
                    top_tat.sort_values("tat_delta_hours"),
                    x="tat_delta_hours",
                    y=hotspot_field,
                    orientation="h",
                    color="tat_delta_hours",
                    color_continuous_scale=["#0E5A8A", "#F6E4CE", "#D97706"],
                )
                fig.update_layout(
                    height=420,
                    xaxis_title="Median order-to-verified delta (B - A) in hours",
                    yaxis_title=hotspot_name,
                    coloraxis_showscale=False,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(255,255,255,0.82)",
                )
                st.plotly_chart(fig, use_container_width=True)

            with row2:
                st.markdown(f"##### Largest {event_name} Gaps")
                fig = px.bar(
                    top_event.sort_values("event_delta_pp"),
                    x="event_delta_pp",
                    y=hotspot_field,
                    orientation="h",
                    color="event_delta_pp",
                    color_continuous_scale=["#0E5A8A", "#F6E4CE", "#D97706"],
                )
                fig.update_layout(
                    height=420,
                    xaxis_title=f"{event_name} delta (B - A) in percentage points",
                    yaxis_title=hotspot_name,
                    coloraxis_showscale=False,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(255,255,255,0.82)",
                )
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("##### Hotspot Table")
            table = hotspot_df[
                [
                    hotspot_field,
                    f"n_A: {cohort_a}",
                    f"n_B: {cohort_b}",
                    f"median_tat_A: {cohort_a}",
                    f"median_tat_B: {cohort_b}",
                    "tat_delta_hours",
                    "event_delta_pp",
                ]
            ].copy()
            st.download_button(
                "Download hotspot table as CSV",
                data=table.to_csv(index=False).encode("utf-8"),
                file_name="hotspot_table.csv",
                mime="text/csv",
            )
            st.dataframe(
                table.style.format(
                    {
                        f"n_A: {cohort_a}": "{:,.0f}",
                        f"n_B: {cohort_b}": "{:,.0f}",
                        f"median_tat_A: {cohort_a}": "{:.2f}",
                        f"median_tat_B: {cohort_b}": "{:.2f}",
                        "tat_delta_hours": "{:+.2f}",
                        "event_delta_pp": "{:+.2f}",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    with details_tab:
        st.markdown("#### Details On Demand")
        detail_cols = [
            "test_code",
            "event_street",
            "test_performing_dept",
            "ordered_weekday_name",
            "is_cancelled",
            "selected_event_flag",
            "hours_order_to_collect",
            "hours_collect_to_receipt",
            "hours_receipt_to_verified",
            "hours_order_to_verified",
            "comparison_label",
        ]
        details = (
            df[detail_cols]
            .sort_values(["comparison_label", "hours_order_to_verified"], ascending=[True, False])
            .head(200)
            .copy()
        )
        st.download_button(
            "Download filtered details as CSV",
            data=details.to_csv(index=False).encode("utf-8"),
            file_name="filtered_specimen_journey_details.csv",
            mime="text/csv",
        )
        st.dataframe(
            details.style.format(
                {
                    "hours_order_to_collect": "{:.2f}",
                    "hours_collect_to_receipt": "{:.2f}",
                    "hours_receipt_to_verified": "{:.2f}",
                    "hours_order_to_verified": "{:.2f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("Method notes", expanded=False):
            st.markdown(
                f"""
                - The dashboard uses one row per ordered test from the derived parquet table.
                - Timeline positions are median elapsed hours from the ordered timestamp.
                - Stage comparison also uses median durations to reduce sensitivity to long tails.
                - Current event definition: {event_description}
                - Threshold-based events use the current filtered comparison scope, not a global constant across all views.
                - Cross-year anomalies can be excluded from the sidebar.
                """
            )


def main() -> None:
    if not DATA_PATH.exists():
        st.error(
            "Derived analysis data was not found. Run `python3 scripts/build_ordered_test_metrics.py` first."
        )
        return

    df = load_data(str(DATA_PATH))
    filtered = apply_base_filters(df)
    compared, comparison_name, cohort_a, cohort_b = comparison_controls(filtered)
    event_name = risk_event_controls()
    thresholds = event_thresholds(compared if not compared.empty else filtered)
    compared, event_description = apply_risk_event(compared, event_name, thresholds)
    render_dashboard(compared, comparison_name, cohort_a, cohort_b, event_name, event_description)


if __name__ == "__main__":
    main()
