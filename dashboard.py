import streamlit as st
import duckdb
import os
import pandas as pd
import plotly.express as px

# -------------------------------------------------------------
# Configuration & Theming
# -------------------------------------------------------------
st.set_page_config(page_title="CIPHER | Threat Analytics", page_icon="🔐", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* Global App Background */
    .stApp {
        background-color: #030303;
        color: #E0E0E0;
    }
    
    /* Hide top header bar */
    header {visibility: hidden;}
    
    /* Neon Typography */
    .title-container {
        padding-bottom: 1.5rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 2rem;
    }
    .neon-text {
        background: linear-gradient(90deg, #FF3366, #FF9933);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5rem;
        font-weight: 900;
        letter-spacing: -1.5px;
        margin: 0;
        padding: 0;
    }
    .subtitle {
        color: #888888;
        font-size: 1.1rem;
        font-weight: 500;
        margin-top: 5px;
        letter-spacing: 0.5px;
    }
    
    /* Premium Glassmorphism Cards */
    .metric-container {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.02);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        flex: 1;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        border: 1px solid rgba(255, 51, 102, 0.4);
        box-shadow: 0 10px 20px rgba(255, 51, 102, 0.1);
    }
    .metric-title {
        color: #888888;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 15px;
        font-weight: 600;
    }
    .metric-value {
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -1px;
    }
    .text-green { color: #00E676; }
    .text-red { color: #FF3366; }
    .text-blue { color: #00A3FF; }
    
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title-container"><h1 class="neon-text">🔐 CIPHER</h1><p class="subtitle">Real-time Impossible Travel Detection & Geolocation Analytics</p></div>', unsafe_allow_html=True)

# -------------------------------------------------------------
# Data Processing (DuckDB)
# -------------------------------------------------------------
PROCESSED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "processed")

if not os.path.exists(PROCESSED_DIR):
    st.error("Datalake Offline. Execute `python local_etl.py` to provision the Parquet architecture.")
    st.stop()

con = duckdb.connect(database=':memory:')

try:
    total_logs_query = f"SELECT count(*) FROM read_parquet('{PROCESSED_DIR}/*/*/*/*.parquet', hive_partitioning=1)"
    total_logs = con.execute(total_logs_query).fetchone()[0]
except Exception as e:
    st.error(f"Datalake query failed: {e}")
    st.stop()

# Query the Impossible Travel
anomaly_query = f"""
WITH UserLogins AS (
  SELECT user_name, event_time, ip_address, country, event_name, event_id
  FROM read_parquet('{PROCESSED_DIR}/*/*/*/*.parquet', hive_partitioning=1)
  WHERE event_name = 'ConsoleLogin'
),
LoginVariations AS (
  SELECT
    a.user_name,
    a.event_time AS login_time_1,
    a.ip_address AS ip_1,
    a.country AS country_1,
    b.event_time AS login_time_2,
    b.ip_address AS ip_2,
    b.country AS country_2,
    date_diff('minute', a.event_time, b.event_time) as minutes_between
  FROM UserLogins a
  JOIN UserLogins b
    ON a.user_name = b.user_name
    AND a.event_id != b.event_id
  WHERE a.event_time < b.event_time
    AND a.country != b.country
    AND date_diff('minute', a.event_time, b.event_time) < 360
)
SELECT * FROM LoginVariations ORDER BY minutes_between ASC
"""
anomalies_df = con.execute(anomaly_query).df()
total_anomalies = len(anomalies_df)

# -------------------------------------------------------------
# Render UI Components
# -------------------------------------------------------------

# Metrics Row
st.markdown(f"""
<div class="metric-container">
    <div class="metric-card">
        <div class="metric-title">Events Traced</div>
        <p class="metric-value text-green">{total_logs:,}</p>
    </div>
    <div class="metric-card">
        <div class="metric-title">Critical Threats</div>
        <p class="metric-value text-red">{total_anomalies:,}</p>
    </div>
    <div class="metric-card">
        <div class="metric-title">Query Engine</div>
        <p class="metric-value text-blue">DuckDB</p>
    </div>
</div>
""", unsafe_allow_html=True)


if total_anomalies > 0:
    chart_col, data_col = st.columns([1.2, 1])
    
    with chart_col:
        st.markdown("<h3 style='color: #E0E0E0; font-weight: 300; margin-bottom: 20px;'>Volume by <span style='color: #FF3366; font-weight: 700;'>Origin</span></h3>", unsafe_allow_html=True)
        country_counts = anomalies_df['country_1'].value_counts().reset_index()
        country_counts.columns = ['Country', 'Incidents']
        
        # Plotly dark aesthetic
        fig = px.bar(
            country_counts, 
            x="Country", 
            y="Incidents",
            color="Incidents", 
            color_continuous_scale=["#1A0000", "#FF3366"],
            template="plotly_dark"
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=0, l=0, r=0, b=0),
            xaxis_title="",
            yaxis_title=""
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with data_col:
        st.markdown("<h3 style='color: #E0E0E0; font-weight: 300; margin-bottom: 20px;'>Active <span style='color: #FF3366; font-weight: 700;'>Alerts</span></h3>", unsafe_allow_html=True)
        
        # Displaying a clean table of the data
        disp_df = anomalies_df[['user_name', 'country_1', 'country_2', 'minutes_between']].rename(
            columns={"user_name": "Target User", "country_1": "Location A", "country_2": "Location B", "minutes_between": "Δ Mins"}
        )
        st.dataframe(disp_df, use_container_width=True, hide_index=True)

else:
    st.success("System Secure. No 'Impossible Travel' locational disparities detected in the current datalake.")
