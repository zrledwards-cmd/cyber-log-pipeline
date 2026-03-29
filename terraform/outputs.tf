output "raw_logs_bucket" {
  description = "S3 bucket for raw JSON logs"
  value       = aws_s3_bucket.raw_logs.bucket
}

output "processed_logs_bucket" {
  description = "S3 bucket for Parquet logs"
  value       = aws_s3_bucket.processed_logs.bucket
}

output "glue_job_name" {
  description = "AWS Glue Job Name"
  value       = aws_glue_job.etl_job.name
}

output "kinesis_firehose_stream_name" {
  description = "Kinesis Firehose Delivery Stream Name"
  value       = aws_kinesis_firehose_delivery_stream.log_stream.name
}

output "athena_database_name" {
  description = "Athena Database Name"
  value       = aws_athena_database.cyber_db.name
}
