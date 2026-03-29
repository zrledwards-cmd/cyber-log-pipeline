import streamlit as st
import duckdb
import os
import pandas as pd

# Page Configuration for the Web App
st.set_page_config(page_title="Cyber Log Dashboard", page_icon="🛡️", layout="wide")

# Paths
PROCESSED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "processed")

# App Header
st.title("🛡️ Cybersecurity Log Analytics")
st.markdown("Live tracking of **'Impossible Travel'** threat anomalies detected directly from the partitioned Parquet datalake.")

# Check if data exists
if not os.path.exists(PROCESSED_DIR):
    st.error("🚨 No processed Parquet data found! Please execute `python local_etl.py` in your terminal to generate the datalake before opening the dashboard.")
    st.stop()

# Connect to DuckDB native memory instance
con = duckdb.connect(database=':memory:')

try:
    # 1. Total Logs Processed Metric
    total_logs_query = f"SELECT count(*) FROM read_parquet('{PROCESSED_DIR}/*/*/*/*.parquet', hive_partitioning=1)"
    total_logs = con.execute(total_logs_query).fetchone()[0]
except Exception as e:
    st.error(f"Error reading Parquet directories via DuckDB: {e}")
    st.stop()

# 2. Main Analytics Query
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

# Render Metrics
st.markdown("---")
col1, col2, col3 = st.columns(3)
col1.metric(label="Total Logs Scanned", value=f"{total_logs:,}")
col2.metric(label="Threat Anomalies Detected", value=f"{total_anomalies}", delta=f"{total_anomalies} Impossible Travel Alerts", delta_color="inverse")
col3.metric(label="Data Engine Status", value="Online", delta="DuckDB Direct Integration")
st.markdown("---")

# Render Tables and Graphs
st.subheader("🚨 Impossible Travel Event Logs")
if total_anomalies == 0:
    st.success("System Secure. No 'Impossible Travel' locational disparities detected in the current datalake.")
else:
    # Stylize the dataframe display
    st.dataframe(
        anomalies_df.style.highlight_max(axis=0, color='#ffcccc'), 
        use_container_width=True
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📊 Anomalies by Origin Country")
    
    # Simple count grouping for a bar chart
    country_counts = anomalies_df['country_1'].value_counts().reset_index()
    country_counts.columns = ['Country', 'Anomalies Triggered']
    st.bar_chart(country_counts, x="Country", y="Anomalies Triggered", color="#ff4b4b")

st.markdown("""
    <br><br>
    <div style="text-align: center; color: gray;">
        <small>Real-time OLAP querying powered by <a href="https://duckdb.org/">DuckDB</a></small>
    </div>
""", unsafe_allow_html=True)
