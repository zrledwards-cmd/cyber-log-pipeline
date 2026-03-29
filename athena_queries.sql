-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS cyber_security_logs;

-- Switch to database (run carefully as statements depend on your Athena setup)
-- USE cyber_security_logs;

-- 1. Create External Table for the Parquet logs processed by Glue
CREATE EXTERNAL TABLE IF NOT EXISTS cyber_security_logs.cloudtrail_logs_parquet (
  event_version STRING,
  user_name STRING,
  account_id STRING,
  event_time TIMESTAMP,
  event_name STRING,
  ip_address STRING,
  country STRING,
  user_agent STRING,
  event_id STRING
)
PARTITIONED BY (
  year INT,
  month INT,
  day INT
)
STORED AS PARQUET
LOCATION 's3://cyber-log-pipeline-processed-logs-bucket/logs_parquet/';

-- Note: You would run `MSCK REPAIR TABLE cyber_security_logs.cloudtrail_logs_parquet`
-- to load the partitions after Glue writes them.


-- 2. Query to detect "Impossible Travel"
-- This query looks for logins from the same user, from two different countries,
-- within a short period of time (e.g., less than 6 hours).

WITH UserLogins AS (
  SELECT
    user_name,
    event_time,
    ip_address,
    country,
    event_name,
    event_id
  FROM
    cyber_security_logs.cloudtrail_logs_parquet
  WHERE
    event_name = 'ConsoleLogin'
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
  FROM
    UserLogins a
  JOIN
    UserLogins b
  ON
    a.user_name = b.user_name
    AND a.event_id != b.event_id
  WHERE
    -- Ensure chronological order to avoid duplicates (A->B and B->A)
    a.event_time < b.event_time
    -- Check if it's a different country
    AND a.country != b.country
    -- Check if it happened within 6 hours (360 minutes)
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
  'Impossible Travel Detected' AS alert_reason
FROM
  LoginVariations
ORDER BY
  minutes_between_logins ASC;
