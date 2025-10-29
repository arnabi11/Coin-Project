
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os, glob

import sys
import warnings

# Ensure the warnings module is correctly registered
sys.modules['warnings'] = warnings

# -----------------------------
# CONFIGURATION
# -----------------------------
# Automatically find the CSV file (adjust path if needed)
#candidates = glob.glob("C:/Users/tanma/Downloads/Coin_Usage_With_SuccessRates (1) (1).csv")
candidates = glob.glob("C:/Users/tanma/OneDrive/Documents/GitHub/Coin-Project\Coin_Usage_With_SuccessRates (1) (1).csv")

if not candidates:
    st.error("❌ CSV file not found. Please place 'Coin_Usage_With_SuccessRates.csv' in this folder.")
    st.stop()

file_path = candidates[0]
st.sidebar.success(f"Using file: {os.path.basename(file_path)}")

# -----------------------------
# LOAD DATA
# -----------------------------
move_cols = ["1st Move", "2nd Move", "3rd Move", "4th Move", "5th Move"]
required = ["Coin ID", "SuccessRate", "FailureRate"] + move_cols

df = pd.read_csv(file_path)
missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"Input file missing required columns: {missing}")
    st.stop()

df["Coin ID"] = df["Coin ID"].astype(str)
coins = df["Coin ID"].tolist()



# -----------------------------
# SHARED TRACE DATA
# -----------------------------
# --- Heatmap data
heatmap_df = df.set_index("Coin ID")[move_cols].fillna(0).astype(int)
heatmap_z = heatmap_df.values
heatmap_x = move_cols
heatmap_y = heatmap_df.index.tolist()

z_min, z_max = float(np.min(heatmap_z)), float(np.max(heatmap_z))
z_mid = (z_min + z_max) / 2.0 if z_max > z_min else z_max
annotations = []
for yi, row_name in enumerate(heatmap_y):
    for xi, col_name in enumerate(heatmap_x):
        val = heatmap_z[yi][xi]
        text_color = "white" if val >= z_mid else "black"
        annotations.append(dict(
            x=col_name, y=row_name, text=str(int(val)),
            showarrow=False, font=dict(color=text_color, size=11)
        ))

# -----------------------------
# DEFINE PLOTS
# -----------------------------
def plot():
    """Overview"""

    # ---------------------------------------
    # 🪙 Description / Intro for the Home Page
    # ---------------------------------------
    st.markdown("""
    ### 🪙 Welcome to the Coin Puzzle Dashboard

    The **Coin Puzzle Project** is a data-driven visualization that explores how different coins perform 
    across various success and failure scenarios.

    This dashboard helps analyze **coin usage patterns**, **performance trends**, and **success ratios** 
    over time — enabling better decision-making and insights into behavioral dynamics.

    Each section provides an interactive view of data distributions, comparisons, and outcomes.  
    Use the **tabs above** to navigate through detailed visualizations.
    """)

    # ---------------------------------------
    # 🔺 Create Triangle Layout for Coins (A–J)
    # ---------------------------------------
    coins = list("ABCDEFGHIJ")

    # Coordinates forming a triangle arrangement
    coords = [
        (0, 0),                  # A - top
        (-1, -1), (1, -1),       # B, C
        (-2, -2), (0, -2), (2, -2),   # D, E, F
        (-3, -3), (-1, -3), (1, -3), (3, -3)  # G, H, I, J
    ]

    x, y = zip(*coords)

    # ---------------------------------------
    # 📊 Create Plotly Figure
    # ---------------------------------------
    fig = go.Figure()

    # Add coin markers (as gold circles with labels)
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode="markers+text",
        text=coins,
        textfont=dict(size=20, color="#1a1a1a", family="Arial Black"),
        textposition="middle center",
        marker=dict(
            size=80,
            color="#f9d342",  # rich gold
            line=dict(color="#1a1a1a", width=2),
            symbol="circle"
        ),
        hoverinfo="text",
        name="Coins"
    ))

    # ---------------------------------------
    # 🎨 Layout Styling
    # ---------------------------------------
    fig.update_layout(
        title="🔺 Coin Puzzle: Triangular Arrangement of Coins A–J",
        title_x=0.5,
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=600,
        margin=dict(t=80, l=10, r=10, b=20),
        showlegend=False
    )

    # ---------------------------------------
    # ✅ Return the Figure
    # ---------------------------------------
    return fig

def plot1():
    """Coin usage by movement order"""
    fig = go.Figure()
    for move in move_cols:
        fig.add_trace(go.Bar(x=coins, y=df[move].fillna(0).astype(int), name=move))
    fig.update_layout(
        title="Plot 1: Coin Usage in First 5 Moves",
        xaxis_title="Coin ID",
        yaxis_title="Number of Times Moved",
        barmode="group",
        height=800, width=1000,
        margin=dict(l=10, r=10, t=30, b=10)
    )
    return fig

def plot2():
    """Success and Failure Rate per Coin"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=coins, y=df["SuccessRate"], mode="lines+markers", name="SuccessRate"))
    fig.add_trace(go.Scatter(x=coins, y=df["FailureRate"], mode="lines+markers", name="FailureRate"))
    fig.update_layout(
        title="Plot 2: Success and Failure Rates (When Coin Was First Move)",
        xaxis_title="Coin ID",
        yaxis_title="Rate",
        yaxis=dict(range=[0, 1.05]),
        height=700,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    return fig

def plot3():
    """Heatmap of Coin Usage"""
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_z, x=heatmap_x, y=heatmap_y,
        colorscale="Blues",
        colorbar=dict(title="Usage Count"),
        hovertemplate="Coin: %{y}<br>Move: %{x}<br>Count: %{z}<extra></extra>"
    ))
    fig.update_layout(
        title="Plot 3: Heatmap of Coin Usage by Movement Order",
        annotations=annotations,
        height=700, 
        margin=dict(l=50, r=50, t=80, b=50)
    )
    return fig

def plot4(coin_id):
    """Per-Coin Success vs Failure (converted from ipywidgets version)"""
    # Compute success/failure counts
    if ("Success" in df.columns) and ("Failure" in df.columns):
        df_counts = df.set_index("Coin ID")[["Success", "Failure"]].fillna(0)
    else:
        # Estimate counts from success/failure rate * first-move occurrences
        first_move_counts = df.set_index("Coin ID")["1st Move"].fillna(0)
        sr = df.set_index("Coin ID")["SuccessRate"].fillna(0)
        fr = df.set_index("Coin ID")["FailureRate"].fillna(0)
        est_succ = (sr * first_move_counts).round().astype(int)
        est_fail = (fr * first_move_counts).round().astype(int)
        df_counts = pd.DataFrame({"Success": est_succ, "Failure": est_fail})

    # Safely handle missing coin
    if coin_id not in df_counts.index:
        st.warning(f"No data available for Coin ID {coin_id}")
        return go.Figure()

    # Extract selected coin’s success/failure values
    row = df_counts.loc[coin_id]
    success_count = int(row["Success"])
    failure_count = int(row["Failure"])

    # Create Plotly bar chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Success", "Failure"],
        y=[success_count, failure_count],
        marker_color=["green", "red"],
        text=[f"{success_count}", f"{failure_count}"],
        textposition="auto",
        name=f"Coin {coin_id}"
    ))
    fig.update_layout(
        title=f" Success and Failure Count for Coin '{coin_id}' (as 1st Move)",
        yaxis_title="User Count",
        xaxis_title="Outcome",
        bargap=0.5,
        height=800,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    return fig


# -----------------------------
# PAGE CONFIGURATION
# -----------------------------
st.set_page_config(
    page_title="🪙 Coin Project Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------
# CUSTOM CSS STYLING (PASTEL THEME)
# -----------------------------
st.markdown("""
    <style>
        /* General background and font */
        body, [class*="stApp"] {
            background: linear-gradient(135deg, #f8f9fa, #e8eaf6, #fce4ec);
            color: #4b4b4b;
            font-family: 'Poppins', sans-serif;
        }

        /* Title styling */
        h1 {
            color: #6b5b95 !important;
            text-align: center;
            padding: 0.5rem 0;
        }

        /* Tabs styling */
        div[data-baseweb="tab-list"] {
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            background-color: rgba(255, 255, 255, 0.7);
            border-radius: 12px;
            padding: 0.6rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }

        div[data-baseweb="tab"] {
            color: #6b5b95;
            font-size: 1.05rem;
            font-weight: 500;
            transition: all 0.3s ease;
        }

        div[data-baseweb="tab"]:hover {
            color: #f06292;
            transform: scale(1.05);
        }

        div[data-baseweb="tab"][aria-selected="true"] {
            background-color: #b2ebf2;
            color: #37474f;
            border-radius: 10px;
            font-weight: 600;
            box-shadow: 0 0 10px rgba(178, 235, 242, 0.6);
        }

        /* Plot area */
        .stPlotlyChart {
            border-radius: 15px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.05);
            background-color: rgba(255, 255, 255, 0.8);
            padding: 15px;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------
# JAVASCRIPT EFFECT (Optional animation)
# -----------------------------
st.markdown("""
    <script>
        // Add subtle fade-in effect when switching tabs
        const observer = new MutationObserver(() => {
            document.querySelectorAll('.element-container').forEach(el => {
                el.style.opacity = 0;
                setTimeout(() => el.style.opacity = 1, 200);
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    </script>
""", unsafe_allow_html=True)

# -----------------------------
# DASHBOARD TITLE
# -----------------------------
st.title("🪙 Copernicus Dashboard")

# -----------------------------
# TAB LAYOUT FOR PLOTS
# -----------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🪙 Home",
    "📊 Plot 1", 
    "📈 Plot 2", 
    "📉 Plot 3", 
    "🎯 Coin-wise Success/Failure"
])

# -----------------------------
# TAB 1 - Plot 1
# -----------------------------
with tab1:
    st.subheader("Overview")
    st.plotly_chart(plot(), use_container_width=True)

# -----------------------------
# TAB 1 - Plot 1
# -----------------------------
with tab2:
    st.subheader("Plot 1: Coin Usage")
    st.plotly_chart(plot1(), use_container_width=True)

# -----------------------------
# TAB 2 - Plot 2
# -----------------------------
with tab3:
    st.subheader("Plot 2: Detailed Distribution")
    st.plotly_chart(plot2(), use_container_width=True)

# -----------------------------
# TAB 3 - Plot 3
# -----------------------------
with tab4:
    st.subheader("Plot 3: Comparative Analysis")
    st.plotly_chart(plot3(), use_container_width=True)

# -----------------------------
# TAB 4 - Coin-wise Analysis
# -----------------------------
with tab5:
    st.subheader("Plot 4: Success vs Failure by Coin ID")
    selected_coin = st.selectbox("Select Coin ID:", options=coins, index=0)
    st.plotly_chart(plot4(selected_coin), use_container_width=True)
