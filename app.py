from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="Specimen Journey Dashboard",
    page_icon="🧪",
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
        return df.iloc[0:0], comparison_field, "", ""

    default_a = available_values[0]
    default_b = available_values[1]
    if comparison_field == "cohort_weekpart":
        default_a = "Weekday" if "Weekday" in available_values else available_values[0]
        default_b = "Weekend" if "Weekend" in available_values else available_values[1]

    cohort_a = st.sidebar.selectbox("Cohort A", available_values, index=available_values.index(default_a))
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


def summarize_group(group_df: pd.DataFrame) -> dict[str, float | int]:
    return {
        "n": int(group_df.shape[0]),
        "completed": int(group_df["is_completed"].sum()),
        "cancel_rate": float(group_df["is_cancelled"].mean()) if len(group_df) else 0.0,
        "median_tat": float(group_df["hours_order_to_verified"].dropna().median())
        if group_df["hours_order_to_verified"].notna().any()
        else float("nan"),
        "median_collect": float(group_df["hours_order_to_collect"].dropna().median())
        if group_df["hours_order_to_collect"].notna().any()
        else float("nan"),
    }


def build_timeline_frame(df: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for label, event_col, start_col in MILESTONE_SPECS:
        elapsed = (df[event_col] - df[start_col]).dt.total_seconds() / 3600.0
        tmp = pd.DataFrame(
            {
                "comparison_label": df["comparison_label"],
                "milestone": label,
                "elapsed_hours": elapsed,
            }
        ).dropna()
        tmp = tmp[tmp["elapsed_hours"] >= 0]
        if tmp.empty:
            continue
        summary = (
            tmp.groupby(["comparison_label", "milestone"], as_index=False)["elapsed_hours"]
            .median()
        )
        records.append(summary)

    if not records:
        return pd.DataFrame(columns=["comparison_label", "milestone", "elapsed_hours"])
    out = pd.concat(records, ignore_index=True)
    out["milestone"] = pd.Categorical(
        out["milestone"],
        categories=[item[0] for item in MILESTONE_SPECS],
        ordered=True,
    )
    return out.sort_values(["comparison_label", "milestone"])


def build_stage_frame(df: pd.DataFrame) -> pd.DataFrame:
    frames = []
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


def metric_card(column, title: str, value: str, help_text: str):
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


def render_dashboard(df: pd.DataFrame, comparison_name: str, cohort_a: str, cohort_b: str) -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top left, #F9F3E7 0%, rgba(249,243,231,0.65) 25%, rgba(255,255,255,0) 55%),
                    linear-gradient(180deg, #FFFDF9 0%, #F6F1E8 100%);
            }
            div[data-testid="stMetric"] {
                background: #fff;
                border-radius: 12px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Specimen Journey Comparison Dashboard")
    st.caption(
        "Compare average specimen timelines, stage bottlenecks, and cancellation likelihood across mutually exclusive cohorts."
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

    st.markdown(f"### Current Comparison: {comparison_name} | A = `{cohort_a}` vs B = `{cohort_b}`")
    top_cols = st.columns(4)
    metric_card(top_cols[0], "Cohort A sample", f"{summary_a['n']:,}", "ordered tests after filters")
    metric_card(top_cols[1], "Cohort B sample", f"{summary_b['n']:,}", "ordered tests after filters")
    metric_card(
        top_cols[2],
        "Cancellation delta",
        f"{(summary_b['cancel_rate'] - summary_a['cancel_rate']) * 100:+.2f} pp",
        "B minus A cancellation rate",
    )
    metric_card(
        top_cols[3],
        "Median TAT delta",
        f"{summary_b['median_tat'] - summary_a['median_tat']:+.2f} h",
        "B minus A order-to-verified median",
    )

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
                height=380,
                xaxis_title="Median elapsed hours since order",
                yaxis_title="Milestone",
                legend_title="Cohort",
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.8)",
            )
            fig.update_yaxes(autorange="reversed")
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
                    "cancel_rate": summary_a["cancel_rate"],
                    "median_order_to_verified_hours": summary_a["median_tat"],
                },
                {
                    "cohort": f"B: {cohort_b}",
                    "ordered_tests": summary_b["n"],
                    "completed_tests": summary_b["completed"],
                    "cancel_rate": summary_b["cancel_rate"],
                    "median_order_to_verified_hours": summary_b["median_tat"],
                },
            ]
        )
        st.dataframe(
            snapshot.style.format(
                {
                    "ordered_tests": "{:,.0f}",
                    "completed_tests": "{:,.0f}",
                    "cancel_rate": "{:.2%}",
                    "median_order_to_verified_hours": "{:.2f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    lower_left, lower_right = st.columns([1.4, 1.0])

    with lower_left:
        st.markdown("#### Stage Duration Comparison")
        stage_df = build_stage_frame(df)
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
                plot_bgcolor="rgba(255,255,255,0.8)",
            )
            st.plotly_chart(fig, use_container_width=True)

    with lower_right:
        st.markdown("#### Event Likelihood")
        likelihood_df = pd.DataFrame(
            {
                "cohort": [f"A: {cohort_a}", f"B: {cohort_b}"],
                "event": ["Cancellation", "Cancellation"],
                "rate": [summary_a["cancel_rate"], summary_b["cancel_rate"]],
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
            yaxis_title="Cancellation rate",
            xaxis_title="",
            showlegend=False,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.8)",
        )
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Current named event is `cancellation_dt`. This can expand later if more event types are modeled.")

    st.markdown("#### Details On Demand")
    detail_cols = [
        "test_code",
        "event_street",
        "test_performing_dept",
        "ordered_weekday_name",
        "is_cancelled",
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


def main() -> None:
    if not DATA_PATH.exists():
        st.error(
            "Derived analysis data was not found. Run `python3 scripts/build_ordered_test_metrics.py` first."
        )
        return

    df = load_data(str(DATA_PATH))
    filtered = apply_base_filters(df)
    compared, comparison_name, cohort_a, cohort_b = comparison_controls(filtered)
    render_dashboard(compared, comparison_name, cohort_a, cohort_b)


if __name__ == "__main__":
    main()
