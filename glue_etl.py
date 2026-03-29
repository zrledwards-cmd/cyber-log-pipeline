import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

# Parse arguments
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_INPUT_PATH', 'S3_OUTPUT_PATH'])

# Initialize contexts
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

input_path = args['S3_INPUT_PATH']
output_path = args['S3_OUTPUT_PATH']

print("Starting custom ETL to transform CloudTrail JSON logs to Parquet...")

# 1. Read JSON logs from S3 Drop bucket using a DynamicFrame
dynamic_frame_read = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [input_path], "recurse": True},
    format="json",
    transformation_ctx="dynamic_frame_read"
)

# 2. Select and cast specific fields to ensure schema consistency
# Mapping (source_column, source_type, target_column, target_type)
mapped_frame = ApplyMapping.apply(
    frame=dynamic_frame_read,
    mappings=[
        ("eventVersion", "string", "event_version", "string"),
        ("userIdentity.userName", "string", "user_name", "string"),
        ("userIdentity.accountId", "string", "account_id", "string"),
        ("eventTime", "string", "event_time", "timestamp"),
        ("eventName", "string", "event_name", "string"),
        ("sourceIPAddress", "string", "ip_address", "string"),
        ("country", "string", "country", "string"),
        ("userAgent", "string", "user_agent", "string"),
        ("eventID", "string", "event_id", "string")
    ],
    transformation_ctx="mapped_frame"
)

# 3. Convert DynamicFrame to Spark DataFrame to add partition columns based on event_time
df = mapped_frame.toDF()

from pyspark.sql.functions import year, month, dayofmonth

# Extract Year, Month, Day for partitioning
df_partitioned = df.withColumn("year", year("event_time")) \
                   .withColumn("month", month("event_time")) \
                   .withColumn("day", dayofmonth("event_time"))

# Convert back to DynamicFrame for writing
dynamic_frame_write = glueContext.create_dynamic_frame.from_DF(df_partitioned, glueContext, "dynamic_frame_write")

# 4. Write Data to S3 in Parquet Format partitioned by year/month/day
glueContext.write_dynamic_frame.from_options(
    frame=dynamic_frame_write,
    connection_type="s3",
    connection_options={
        "path": output_path,
        "partitionKeys": ["year", "month", "day"]
    },
    format="parquet",
    transformation_ctx="dynamic_frame_write"
)

job.commit()
