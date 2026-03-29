import duckdb
import os
import pandas as pd

# Setting pandas configuration to display all columns nicely
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

PROCESSED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "processed")

def main():
    if not os.path.exists(PROCESSED_DIR):
        print("Processed data not found. Please run local_etl.py first.")
        return

    print("Connecting to DuckDB memory instance...")
    con = duckdb.connect(database=':memory:')

    # Using DuckDB's native read_parquet function which supports Hive partitioning automatically
    query = f"""
    WITH UserLogins AS (
      SELECT
        user_name,
        event_time,
        ip_address,
        country,
        event_name,
        event_id
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
        -- Calculate time difference in minutes
        date_diff('minute', a.event_time, b.event_time) as minutes_between_logins
      FROM UserLogins a
      JOIN UserLogins b
        ON a.user_name = b.user_name
        AND a.event_id != b.event_id
      WHERE a.event_time < b.event_time
        AND a.country != b.country
        AND date_diff('minute', a.event_time, b.event_time) < 360
    )
    SELECT
      user_name,
      country_1,
      ip_1,
      login_time_1,
      country_2,
      ip_2,
      login_time_2,
      minutes_between_logins,
      'Impossible Travel' AS alert_reason
    FROM LoginVariations
    ORDER BY minutes_between_logins ASC;
    """

    print("Executing 'Impossible Travel' query against Local Parquet files...")
    
    try:
        results = con.execute(query).df()
        
        if results.empty:
            print("\nNo Impossible Travel events found.")
        else:
            print("\n🔥 ANOMALIES DETECTED 🔥\n")
            print(results.to_markdown(index=False))
    except Exception as e:
        print(f"An error occurred querying DuckDB: {e}")

if __name__ == "__main__":
    main()
