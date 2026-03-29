terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# -------------------------------------------------------------
# 1. S3 Buckets
# -------------------------------------------------------------
resource "aws_s3_bucket" "raw_logs" {
  bucket        = "${var.project_name}-raw-logs-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket" "processed_logs" {
  bucket        = "${var.project_name}-processed-logs-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

# Helper to get AWS Account ID to ensure globally unique bucket names
data "aws_caller_identity" "current" {}

# -------------------------------------------------------------
# 2. IAM Roles and Policies
# -------------------------------------------------------------
# Role for Glue
resource "aws_iam_role" "glue_role" {
  name = "${var.project_name}-glue-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "glue_s3_policy" {
  name        = "${var.project_name}-glue-s3-policy"
  description = "Allow Glue to read raw S3 and write to processed S3"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:DeleteObject"
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.raw_logs.arn,
          "${aws_s3_bucket.raw_logs.arn}/*",
          aws_s3_bucket.processed_logs.arn,
          "${aws_s3_bucket.processed_logs.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_s3_attach" {
  role       = aws_iam_role.glue_role.name
  policy_arn = aws_iam_policy.glue_s3_policy.arn
}

resource "aws_iam_role_policy_attachment" "glue_service_attach" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Role for Firehose
resource "aws_iam_role" "firehose_role" {
  name = "${var.project_name}-firehose-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "firehose.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "firehose_policy" {
  name        = "${var.project_name}-firehose-policy"
  description = "Allow Firehose to write to S3 bucket"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:AbortMultipartUpload",
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:ListBucketMultipartUploads",
          "s3:PutObject"
        ],
        Resource = [
          aws_s3_bucket.raw_logs.arn,
          "${aws_s3_bucket.raw_logs.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "firehose_attach" {
  role       = aws_iam_role.firehose_role.name
  policy_arn = aws_iam_policy.firehose_policy.arn
}

# -------------------------------------------------------------
# 3. AWS Glue Job
# -------------------------------------------------------------
resource "aws_glue_job" "etl_job" {
  name         = "${var.project_name}-glue-job"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "4.0"
  timeout      = 60
  
  worker_type       = "G.1X"
  number_of_workers = 2

  command {
    script_location = "s3://${aws_s3_bucket.raw_logs.bucket}/scripts/glue_etl.py"
    python_version  = "3"
  }

  default_arguments = {
    "--S3_INPUT_PATH"       = "s3://${aws_s3_bucket.raw_logs.bucket}/logs/"
    "--S3_OUTPUT_PATH"      = "s3://${aws_s3_bucket.processed_logs.bucket}/logs_parquet/"
    "--job-language"        = "python"
    "--job-bookmark-option" = "job-bookmark-disable"
  }
}

# -------------------------------------------------------------
# 4. Amazon Athena Database
# -------------------------------------------------------------
resource "aws_athena_database" "cyber_db" {
  name   = "cyber_security_logs"
  bucket = aws_s3_bucket.processed_logs.bucket
}

# -------------------------------------------------------------
# 5. Amazon Kinesis Data Firehose
# -------------------------------------------------------------
resource "aws_kinesis_firehose_delivery_stream" "log_stream" {
  name        = "${var.project_name}-stream"
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn   = aws_iam_role.firehose_role.arn
    bucket_arn = aws_s3_bucket.raw_logs.arn
    
    # Store incoming records into the logs/ prefix
    prefix = "logs/"
    
    # Force flushing rapidly for demonstration/testing purposes
    buffering_size     = 1
    buffering_interval = 60 
  }
}
