import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, year, month, dayofmonth, to_timestamp

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

def main():
    print("Initializing Local PySpark Data ETL Job...")
    spark = SparkSession.builder \
        .appName("CyberLogETL") \
        .master("local[*]") \
        .getOrCreate()

    # Disable noisy logging
    spark.sparkContext.setLogLevel("ERROR")

    if not os.path.exists(RAW_DIR) or not os.listdir(RAW_DIR):
        print(f"No raw files found in {RAW_DIR}. Run generate_logs.py first.")
        return

    # 1. Read JSON logs
    print(f"Reading JSON logs from {RAW_DIR}")
    raw_df = spark.read.json(f"{RAW_DIR}/*.json")

    # 2. Extract and cast specific fields to enforce schema
    processed_df = raw_df.select(
        col("eventVersion").alias("event_version").cast("string"),
        col("userIdentity.userName").alias("user_name").cast("string"),
        col("userIdentity.accountId").alias("account_id").cast("string"),
        to_timestamp(col("eventTime")).alias("event_time"),
        col("eventName").alias("event_name").cast("string"),
        col("sourceIPAddress").alias("ip_address").cast("string"),
        col("country").alias("country").cast("string"),
        col("userAgent").alias("user_agent").cast("string"),
        col("eventID").alias("event_id").cast("string")
    )

    # 3. Add Partition Columns
    partitioned_df = processed_df \
        .withColumn("year", year("event_time")) \
        .withColumn("month", month("event_time")) \
        .withColumn("day", dayofmonth("event_time"))

    # 4. Write data to Parquet in the processed folder
    print(f"Writing Parquet data to {PROCESSED_DIR}")
    
    partitioned_df.write \
        .partitionBy("year", "month", "day") \
        .mode("overwrite") \
        .parquet(PROCESSED_DIR)

    print("ETL Job Finished Successfully!")
    spark.stop()

if __name__ == "__main__":
    main()
