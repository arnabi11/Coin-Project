# main.py

# ---------- Imports ----------
import streamlit as st  # must be imported before any st.* calls
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import io

# ---------- Page config (must be the first Streamlit command) ----------
st.set_page_config(
    page_title="Coin Transition Analytics",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Constants ----------
FILE_DEFAULT = "/Volumes/WORKING/Study/Project/Web/NewWebFinal/JEFile.xlsx"

# ---------- Title ----------
st.title("Coin Transitions  - Time Gap Analytics Dashboard")

st.markdown(
    "Analysis of Time Gaps During Coin Transitions."
)

# ---------- Sidebar: data source ----------
st.sidebar.header("Data source")
source_mode = st.sidebar.radio(
    "Select data source",
    ["Default file", "Upload file"],
    index=0,
)

uploaded_file = None
sheet_input = st.sidebar.text_input(
    "Excel sheet name (optional)",
    value="",
    placeholder="e.g., Sheet1 (blank = first sheet)",
)

if source_mode == "Upload file":
    uploaded_file = st.sidebar.file_uploader(
        "Upload Excel (.xlsx/.xls) or CSV (.csv)",
        type=["xlsx", "xls", "csv"],
    )

# Cache controls
c1, c2 = st.sidebar.columns(2)
with c1:
    if st.button("Clear cache"):
        st.cache_data.clear()
with c2:
    st.caption("Clear after changing files to force fresh load.")

# ---------- Sidebar: controls ----------
st.sidebar.header("Controls")
top_n = st.sidebar.slider(" Number of users (time gap)", 5, 200, 30, 5)
#bottom_n = st.sidebar.slider("Bottom N users (time gap)", 5, 200, 30, 5)
bottom_n = top_n
# ---------- Helpers ----------
def _normalize_sheet_name(x: str | None):
    return x if (x is not None and len(x.strip()) > 0) else 0

def coerce_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    s = series.copy()
    s = s.replace({"True": True, "False": False, "true": True, "false": False, "YES": True, "NO": False})
    try:
        s_num = pd.to_numeric(s, errors="coerce")
        if pd.api.types.is_numeric_dtype(s_num):
            s = s_num.fillna(0).astype(int).astype(bool)
    except Exception:
        s = s.fillna(False)
    return s.astype(bool)

def _validate_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    return [c for c in required if c not in df.columns]

# ---------- Cached loaders ----------
@st.cache_data(show_spinner=True)
def load_data_from_upload(content_bytes: bytes, filename: str, sheet_name: str | int):
    name = (filename or "").lower()
    if name.endswith(".csv"):
        text = content_bytes.decode("utf-8", errors="ignore")
        return pd.read_csv(io.StringIO(text))
    else:
        return pd.read_excel(io.BytesIO(content_bytes), sheet_name=sheet_name, engine="openpyxl")

@st.cache_data(show_spinner=True)
def load_data_from_path(path: str, sheet_name: str | int, mtime: float):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    else:
        return pd.read_excel(p, sheet_name=sheet_name, engine="openpyxl")

# ---------- Acquire data ----------
data = None
load_error = None
load_info = None  # collect status text for footer

try:
    if source_mode == "Upload file":
        if uploaded_file is not None:
            content = uploaded_file.getvalue()
            data = load_data_from_upload(content, uploaded_file.name, _normalize_sheet_name(sheet_input))
            load_info = f"Loaded uploaded file: {uploaded_file.name}"  # footer later
        else:
            st.info("Upload a file to proceed, or switch back to Default file.", icon="📄")
    else:
        p = Path(FILE_DEFAULT)
        if p.exists():
            mtime = p.stat().st_mtime
            data = load_data_from_path(str(p), _normalize_sheet_name(sheet_input), mtime)
            load_info = f"Loaded default file: {FILE_DEFAULT}"  # footer later
        else:
            st.error(f"Default file not found: {FILE_DEFAULT}")
except Exception as e:
    load_error = str(e)

if load_error:
    st.error(f"Error loading  {load_error}")

if data is None:
    st.stop()

# ---------- Validate and clean ----------
expected_cols = ["UserID", "TimeGap_sec", "ProblemSolved", "CoinID_Transition", "Prev_PathID"]
missing = _validate_columns(data, expected_cols)
if missing:
    st.warning(f"Missing expected columns: {missing}")
    st.dataframe(data.head(20), use_container_width=True)
    st.stop()

# Keep both df and file2 for compatibility with your original notebook variables
df = data.copy()
file2 = data.copy()

df["TimeGap_sec"] = pd.to_numeric(df["TimeGap_sec"], errors="coerce").fillna(0.0)
df["ProblemSolved"] = coerce_bool(df["ProblemSolved"])
df["CoinID_Transition"] = df["CoinID_Transition"].astype(str)

file2["TimeGap_sec"] = pd.to_numeric(file2["TimeGap_sec"], errors="coerce").fillna(0.0)
file2["ProblemSolved"] = coerce_bool(file2["ProblemSolved"])
file2["CoinID_Transition"] = file2["CoinID_Transition"].astype(str)

# ---------- Core metrics ----------
unique_user_count = df["UserID"].nunique()

grouped = (
    df.groupby("CoinID_Transition")
    .agg(
        Avg_TimeGap_sec=("TimeGap_sec", "mean"),
        Success_Rate=("ProblemSolved", lambda x: (x == True).mean()),
        Unsuccess_Rate=("ProblemSolved", lambda x: (x == False).mean()),
    )
    .reset_index()
)

by_transition = df.groupby("CoinID_Transition")
avg_succ = by_transition.apply(
    lambda g: df.loc[g.index, "TimeGap_sec"][df.loc[g.index, "ProblemSolved"] == True].mean()
)
avg_unsucc = by_transition.apply(
    lambda g: df.loc[g.index, "TimeGap_sec"][df.loc[g.index, "ProblemSolved"] == False].mean()
)

grouped = (
    grouped.merge(avg_succ.rename("Avg_TimeGap_Success").reset_index(), on="CoinID_Transition", how="left")
           .merge(avg_unsucc.rename("Avg_TimeGap_Unsuccess").reset_index(), on="CoinID_Transition", how="left")
)

overall_means = grouped[["Avg_TimeGap_sec", "Avg_TimeGap_Success", "Avg_TimeGap_Unsuccess", "Success_Rate"]].mean()

# Per-user totals and status
file3 = df.copy()
user_timegap_status = (
    file3.groupby("UserID")["TimeGap_sec"].sum().reset_index().rename(columns={"TimeGap_sec": "Total_TimeGap_sec"})
)
user_status_map = file3.groupby("UserID")["ProblemSolved"].max().map({True: "Success", False: "Unsuccess"})
user_timegap_status["Status"] = user_timegap_status["UserID"].map(user_status_map)
user_timegap_status["Total_TimeGap_sec"] = user_timegap_status["Total_TimeGap_sec"].round(3)
file4 = user_timegap_status

user_timegap_by_status = (
    df.groupby(["UserID", "ProblemSolved"])["TimeGap_sec"]
    .sum()
    .unstack(fill_value=0)
    .rename(columns={True: "Total_TimeGap_Success", False: "Total_TimeGap_Unsuccess"})
    .reset_index()
)
user_timegap_by_status["Total_TimeGap_Success"] = user_timegap_by_status["Total_TimeGap_Success"].round(3)
user_timegap_by_status["Total_TimeGap_Unsuccess"] = user_timegap_by_status["Total_TimeGap_Unsuccess"].round(3)

file5 = user_timegap_by_status.merge(
    user_timegap_status[["UserID", "Status"]], on="UserID", how="left"
)
file5["Total_TimeGap_All"] = file5["Total_TimeGap_Success"] + file5["Total_TimeGap_Unsuccess"]
file5["Status"] = file5["Status"].fillna("Unsuccess")

# Split transitions into from/to for heatmaps
parts = grouped["CoinID_Transition"].astype(str).str.split("->", n=1, expand=True)
if parts.shape[1] == 2:
    grouped["from"] = parts[0]
    grouped["to"] = parts[1]
else:
    grouped["from"] = grouped["CoinID_Transition"]
    grouped["to"] = grouped["CoinID_Transition"]

# ---------- Tabs (always present) ----------
tab_overview, tab_distributions, tab_users, tab_transitions, tab_heatmaps, tab_pathids, tab_groups = st.tabs(
    ["Overview", "Distributions",  "Users Wise", "CointID Transitions", "Heatmaps", "CoinSequence Wise", "Coin ID Group Wise"]
)

# ---------- Overview ----------
with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Unique Users", f"{unique_user_count:,.0f}")
    c2.metric("Mean TimeGap (All)", f"{overall_means['Avg_TimeGap_sec']:.2f} s")
    c3.metric("Mean TimeGap (Success)", f"{overall_means['Avg_TimeGap_Success']:.2f} s")
    c4.metric("Success Rate (Mean)", f"{overall_means['Success_Rate']:.2%}")

    st.subheader("Grouped Transition Summary")
    st.dataframe(grouped.sort_values("Success_Rate", ascending=False), use_container_width=True)

# ---------- Distributions ----------
with tab_distributions:
    st.subheader("Distribution of Total_TimeGap_sec by User Status")
    palette = {"Success": "blue", "Unsuccess": "darkorange"}
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.histplot(
        data=file4, x="Total_TimeGap_sec", hue="Status",
        bins=50, kde=True, multiple="stack", palette=palette, ax=ax
    )
    ax.set_title("Distribution of Total_TimeGap_sec by User Status")
    ax.set_xlabel("Total_TimeGap_sec")
    ax.set_ylabel("Number of Users")
    st.pyplot(fig)

# ---------- Users ----------
with tab_users:
    color_map = {"Success": "blue", "Unsuccess": "darkorange"}
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=color_map["Success"], label="Success"),
        Patch(facecolor=color_map["Unsuccess"], label="Unsuccess"),
    ]

    st.subheader(f"Top {top_n} Users by Total_TimeGap_sec")
    top_users = file5.sort_values(by="Total_TimeGap_All", ascending=False).head(top_n)
    fig, ax = plt.subplots(figsize=(14, 7))
    colors = top_users["Status"].map(color_map).fillna("gray")
    ax.bar(top_users["UserID"].astype(str), top_users["Total_TimeGap_All"], color=colors)
    ax.set_ylabel("Total_TimeGap_sec")
    ax.set_xlabel("UserID")
    ax.set_title(f"Top {top_n} Users by Total TimeGap_sec (Color: Success/Unsuccess)")
    plt.setp(ax.get_xticklabels(), rotation=90)
    ax.legend(handles=legend_elements, title="Status")
    st.pyplot(fig)

    st.subheader(f"Bottom {bottom_n} Users by Total_TimeGap_sec")
    bottom_users = file5.sort_values(by="Total_TimeGap_All", ascending=True).head(bottom_n)
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = bottom_users["Status"].map(color_map).fillna("gray")
    ax.bar(bottom_users["UserID"].astype(str), bottom_users["Total_TimeGap_All"], color=colors)
    ax.set_title(f"Bottom {bottom_n} Users by Total_TimeGap_sec")
    ax.set_xlabel("UserID")
    ax.set_ylabel("Total_TimeGap_sec")
    plt.setp(ax.get_xticklabels(), rotation=90)
    ax.legend(handles=legend_elements, title="Status")
    st.pyplot(fig)

    st.subheader(f"Highest/Lowest Successful TimeGap (Top {top_n})")
    success_df = file5[file5["Status"] == "Success"]
    top_success = success_df.nlargest(top_n, "Total_TimeGap_Success")
    least_success = success_df.nsmallest(top_n, "Total_TimeGap_Success")

    fig, axes = plt.subplots(1, 2, figsize=(18, 6))
    axes[0].barh(top_success["UserID"].astype(str), top_success["Total_TimeGap_Success"], color="blue")
    axes[0].set_title(f"Top {top_n} Users by Total Successful TimeGap_sec")
    axes[0].set_xlabel("Total_TimeGap_Success")
    axes[0].invert_yaxis()

    axes[1].barh(least_success["UserID"].astype(str), least_success["Total_TimeGap_Success"], color="lightblue")
    axes[1].set_title(f"Lowest {top_n} Users by Total Successful TimeGap_sec")
    axes[1].set_xlabel("Total_TimeGap_Success")
    axes[1].invert_yaxis()
    st.pyplot(fig)

    st.subheader(f"Highest/Lowest Unsuccessful TimeGap (Top {top_n})")
    unsuccess_df = file5[file5["Status"] == "Unsuccess"]
    top_unsuccess = unsuccess_df.nlargest(top_n, "Total_TimeGap_Unsuccess")
    least_unsuccess = unsuccess_df.nsmallest(top_n, "Total_TimeGap_Unsuccess")

    fig, axes = plt.subplots(1, 2, figsize=(18, 6))
    axes[0].barh(top_unsuccess["UserID"].astype(str), top_unsuccess["Total_TimeGap_Unsuccess"], color="darkorange")
    axes[0].set_title(f"Top {top_n} Users by Total Unsuccessful TimeGap_sec")
    axes[0].set_xlabel("Total_TimeGap_Unsuccess")
    axes[0].invert_yaxis()

    axes[1].barh(least_unsuccess["UserID"].astype(str), least_unsuccess["Total_TimeGap_Unsuccess"], color="orange")
    axes[1].set_title(f"Lowest {top_n} Users by Total Unsuccessful TimeGap_sec")
    axes[1].set_xlabel("Total_TimeGap_Unsuccess")
    axes[1].invert_yaxis()
    st.pyplot(fig)

# ---------- Transitions ----------
with tab_transitions:
    st.subheader("Success vs Unsuccess Rates by CoinID_Transition")
    grouped_sorted = grouped.sort_values(by="Success_Rate", ascending=False)
    gap = 1.5
    x = np.arange(len(grouped_sorted)) * gap
    width = 0.5
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.bar(x - width / 2, grouped_sorted["Success_Rate"], width, label="Success Rate", color="blue")
    ax.bar(x + width / 2, grouped_sorted["Unsuccess_Rate"], width, label="Unsuccess Rate", color="darkorange")
    ax.set_xticks(x)
    ax.set_xticklabels(grouped_sorted["CoinID_Transition"], rotation=90)
    ax.set_title("Success and Unsuccess Rates by CoinID_Transition")
    ax.set_xlabel("CoinID_Transition")
    ax.set_ylabel("Rate")
    ax.legend()
    st.pyplot(fig)

    st.subheader("Average TimeGap: Success vs Unsuccess (sorted by Avg TimeGap)")
    grouped_time = grouped.sort_values(by="Avg_TimeGap_sec", ascending=False)
    x = np.arange(len(grouped_time))
    width = 0.35
    fig, ax = plt.subplots(figsize=(16, 6))
    ax.bar(x - width / 2, grouped_time["Avg_TimeGap_Success"].fillna(0), width, label="Avg TimeGap (Success)", color="blue", alpha=0.9)
    ax.bar(x + width / 2, grouped_time["Avg_TimeGap_Unsuccess"].fillna(0), width, label="Avg TimeGap (Unsuccess)", color="darkorange", alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(grouped_time["CoinID_Transition"], rotation=90)
    ax.set_title("Average TimeGap_sec: Success vs Unsuccess by CoinID_Transition")
    ax.set_xlabel("CoinID_Transition")
    ax.set_ylabel("Avg_TimeGap_sec")
    ax.legend()
    st.pyplot(fig)

# ---------- Heatmaps ----------
with tab_heatmaps:
    st.subheader("Avg Successful TimeGap_sec (from → to)")
    success_matrix = grouped.pivot(index="from", columns="to", values="Avg_TimeGap_Success")
    if success_matrix is None or success_matrix.empty or success_matrix.count().sum() == 0:
        st.info("No data available to render the Successful TimeGap heatmap.")
    else:
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(success_matrix.fillna(0), annot=True, fmt=".2f", cmap="Greens",
                    cbar_kws={"label": "Avg Successful TimeGap_sec"}, ax=ax)
        ax.set_xlabel("To CoinID"); ax.set_ylabel("From CoinID")
        ax.set_title("Average Successful TimeGap_sec (from-to)")
        st.pyplot(fig)

    st.subheader("Avg Unsuccessful TimeGap_sec (from → to)")
    unsuccess_matrix = grouped.pivot(index="from", columns="to", values="Avg_TimeGap_Unsuccess")
    if unsuccess_matrix is None or unsuccess_matrix.empty or unsuccess_matrix.count().sum() == 0:
        st.info("No data available to render the Unsuccessful TimeGap heatmap.")
    else:
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(unsuccess_matrix.fillna(0), annot=True, fmt=".2f", cmap="Reds",
                    cbar_kws={"label": "Avg Unsuccessful TimeGap_sec"}, ax=ax)
        ax.set_xlabel("To CoinID"); ax.set_ylabel("From CoinID")
        ax.set_title("Average Unsuccessful TimeGap_sec (from-to)")
        st.pyplot(fig)

# ---------- PathIDs ----------
with tab_pathids:
    st.subheader("CoinID Sequence Analysis")
    ps = (
        df[["UserID", "Prev_PathID", "TimeGap_sec", "ProblemSolved"]]
        .loc[lambda d: d["Prev_PathID"].notna()]
        .rename(columns={"Prev_PathID": "PathID"})
        .reset_index(drop=True)
    )
    if ps.empty:
        st.info("No rows with Prev_PathID found; PathID analysis is unavailable.")
    else:
        ps_agg = (
            ps.groupby("PathID", as_index=True)
            .agg(
                Count=("UserID", "count"),
                Avg_TimeGap_sec=("TimeGap_sec", "mean"),
                Solved_Count=("ProblemSolved", lambda x: (x == True).sum()),
                Unsolved_Count=("ProblemSolved", lambda x: (x == False).sum()),
            )
        )
        if ps_agg.empty:
            st.info("No PathID aggregates available to plot.")
        else:
            denom = ps_agg["Solved_Count"] + ps_agg["Unsolved_Count"]
            ps_agg["Success_Rate"] = ps_agg["Solved_Count"] / denom.replace(0, 1)

            sel_paths = ps_agg["Count"].sort_values(ascending=False).index[:10]
            if len(sel_paths) == 0:
                st.info("No PathIDs to show in charts.")
            else:
                fig, ax = plt.subplots(figsize=(12, 4))
                ps_agg.loc[sel_paths, "Count"].plot(kind="bar", color="tab:blue", ax=ax)
                ax.set_title("Top 10 CoinID Sequence by Count"); ax.set_ylabel("Count"); ax.set_xlabel("PathID")
                plt.setp(ax.get_xticklabels(), rotation=45); st.pyplot(fig)

                fig, ax = plt.subplots(figsize=(12, 4))
                ps_agg.loc[sel_paths, "Avg_TimeGap_sec"].plot(kind="bar", color="tab:orange", ax=ax)
                ax.set_title("Average TimeGap_sec for Top 10 CoinID Sequence"); ax.set_ylabel("Avg_TimeGap_sec"); ax.set_xlabel("PathID")
                plt.setp(ax.get_xticklabels(), rotation=45); st.pyplot(fig)

                sel_low = ps_agg["Avg_TimeGap_sec"].nsmallest(10).sort_values(ascending=True)
                if len(sel_low) > 0:
                    fig, ax = plt.subplots(figsize=(12, 4))
                    sel_low.plot(kind="bar", color="tab:orange", ax=ax)
                    ax.set_title("Average TimeGap_sec for Lowest 10 CoinID sequence")
                    ax.set_ylabel("Avg_TimeGap_sec"); ax.set_xlabel("PathID")
                    plt.setp(ax.get_xticklabels(), rotation=45); st.pyplot(fig)
                else:
                    st.info("No PathIDs with the lowest average time gaps to display.")

# ---------- Groups (chart first, table second) ----------
with tab_groups:
    st.subheader('Group-wise transition summary')

    file2["Group"] = file2["CoinID_Transition"].astype(str).str[0]
    groups = sorted([g for g in file2["Group"].dropna().unique().tolist() if isinstance(g, str) and len(g) > 0])

    if len(groups) == 0:
        st.info("No groups found from CoinID_Transition first characters.")
    else:
        group_choice = st.selectbox(
            "CoinID initial",
            groups,
            index=0,
            help="Select the starting character of CoinID_Transition",
        )

        group_df = file2[file2["Group"] == group_choice]
        if group_df.empty:
            st.info("No rows match this group selection.")
        else:
            summary = (
                group_df.groupby(["CoinID_Transition", "ProblemSolved"])["TimeGap_sec"]
                .mean()
                .reset_index()
                .pivot(index="CoinID_Transition", columns="ProblemSolved", values="TimeGap_sec")
                .rename(columns={True: "Success", False: "Unsuccess"})
                .sort_values(by="Success", ascending=False)
            )

            if summary is None or summary.empty:
                st.info("No data available for this group.")
            else:
                # 1) Bar chart first
                fig, ax = plt.subplots(figsize=(12, 6))
                cols_to_plot = [c for c in ["Success", "Unsuccess"] if c in summary.columns]
                summary[cols_to_plot].fillna(0).plot(kind="bar", ax=ax, color=["blue", "darkorange"][:len(cols_to_plot)])
                ax.set_title(f'Average TimeGap_sec for transitions starting with "{group_choice}" (Success vs Unsuccess)')
                ax.set_xlabel("CoinID_Transition"); ax.set_ylabel("Avg_TimeGap_sec")
                plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
                ax.legend(title="ProblemSolved"); fig.tight_layout()
                st.pyplot(fig)

                # 2) Table below the chart
                st.dataframe(summary.round(3), use_container_width=True)

# ---------- Raw data preview ----------
with st.expander("Show raw data (first 100 rows)"):
    st.dataframe(df.head(100), use_container_width=True)

# ---------- Footer: load message at bottom ----------
if load_info:
    st.caption(load_info)
