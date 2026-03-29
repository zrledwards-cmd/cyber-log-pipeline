# Cloud-Native Cybersecurity Log Pipeline - Cost Analysis Report

The proposed pipeline is extremely cost-effective as it relies on serverless technologies (S3, Glue, Athena). Costs scale with the amount of data processed and queried. Below is an estimated cost breakdown based on an assumed volume of **100 GB of logs ingested per month**, stored in the `US East (N. Virginia)` region.

## 1. Amazon S3 (Storage)
Logs are stored both in raw forms (JSON) and processed (Parquet).

*   **Raw Logs (JSON):** 100 GB
*   **Processed Logs (Parquet):** Highly compressed. Let's assume a 10x compression ratio. 10 GB.
*   **Total Data Stored:** ~110 GB per month (accumulative).
*   **Cost:** S3 Standard storage is ~$0.023 per GB/month.
*   **Calculated Cost:** `110 GB * $0.023 = $2.53/month`.

*Note: Incorporating lifecycle policies (e.g., moving raw JSON to Glacier after 30 days) would continually drive this down.*

## 2. AWS Glue (ETL & Data Catalog)
Glue costs are based on Data Processing Units (DPUs) per hour.

*   **ETL Job:** Let's assume the Glue job runs once daily and takes 10 minutes (0.166 hours) to process the daily delta (~3.3 GB of new data) using 2 DPUs.
*   **Cost Calculation:** `$0.44 per DPU-Hour * 2 DPUs * 0.166 hours/day * 30 days = $4.38/month`.
*   **AWS Glue Data Catalog:** The first million objects stored and first million requests per month are free. We handle far less here, so cost is effectively **$0.00**.

## 3. Amazon Athena (Querying)
Athena pricing is based on the data scanned during a query (`$5.00 per TB scanned`). This is where the conversion to Parquet pays off.

*   **Data Scanned per Query:** Our data is converted to Parquet (~10 GB daily, accumulated) and partitioned by date. A query spanning the last 3 days would scan around 1 GB.
*   **Query Frequency:** Let's say we run our "Impossible Travel" query every hour for monitoring purposes. `720 queries/month`.
*   **Total Data Scanned:** Let's assume on average it scans 1 GB per query. Total `720 GB`.
*   **Calculated Cost:** `(720 GB / 1024 GB) * $5.00 = $3.51/month`.

## Total Estimated Monthly Cost

| Service | Component | Estimated Monthly Cost |
| :--- | :--- | :--- |
| **Amazon S3** | Storage (Raw & Parquet) | **$2.53** |
| **AWS Glue** | Daily ETL Processing | **$4.38** |
| **Amazon Athena**| Hourly Analytical Queries | **$3.51** |
| **Total** | | **$10.42 / month** |

### Cost Optimization Strategies Employed:
1.  **Parquet Conversion:** Transforming JSON to Parquet vastly reduces S3 storage footprint.
2.  **Parquet Columnar querying:** Athena only scans the columns specified in the `SELECT` query, drastically lowering the scanned data volume and query costs relative to querying raw JSON.
3.  **Partitioning:** Organizing data by `year/month/day` means queries with a date filter skip irrelevant days, minimizing data scanning charges.
4.  **Serverless:** No EC2 instances are idling. You only pay when pipelines actually run.
