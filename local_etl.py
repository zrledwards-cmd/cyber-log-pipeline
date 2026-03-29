import os
import duckdb

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

def main():
    print("Initializing DuckDB Local ETL Job...")
    
    if not os.path.exists(RAW_DIR) or not os.listdir(RAW_DIR):
        print(f"No raw files found in {RAW_DIR}. Run generate_logs.py first.")
        return

    con = duckdb.connect(':memory:')

    print(f"Reading JSON logs from {RAW_DIR} and applying schema...")
    
    # 1. Read JSON, cast schema, and add partition columns
    con.execute(f"""
        CREATE VIEW processed_logs AS 
        SELECT 
            CAST(eventVersion AS VARCHAR) AS event_version,
            CAST(userIdentity.userName AS VARCHAR) AS user_name,
            CAST(userIdentity.accountId AS VARCHAR) AS account_id,
            CAST(eventTime AS TIMESTAMP) AS event_time,
            CAST(eventName AS VARCHAR) AS event_name,
            CAST(sourceIPAddress AS VARCHAR) AS ip_address,
            CAST(country AS VARCHAR) AS country,
            CAST(userAgent AS VARCHAR) AS user_agent,
            CAST(eventID AS VARCHAR) AS event_id,
            year(CAST(eventTime AS TIMESTAMP)) AS year,
            month(CAST(eventTime AS TIMESTAMP)) AS month,
            day(CAST(eventTime AS TIMESTAMP)) AS day
        FROM read_json_auto('{RAW_DIR}/*.json')
    """)

    # 2. Write data to Parquet partitioned by year/month/day
    print(f"Writing partitioned Parquet data to {PROCESSED_DIR}...")
    
    con.execute(f"""
        COPY (SELECT * FROM processed_logs) 
        TO '{PROCESSED_DIR}' 
        (FORMAT PARQUET, PARTITION_BY (year, month, day), OVERWRITE_OR_IGNORE true)
    """)

    print("ETL Job Finished Successfully!")
    
if __name__ == "__main__":
    main()
