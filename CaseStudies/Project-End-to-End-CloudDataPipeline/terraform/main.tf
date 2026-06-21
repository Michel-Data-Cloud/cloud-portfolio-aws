################################################################################
# PROJECT 1 — END-TO-END AWS DATA PIPELINE
# Complete Infrastructure as Code
#
# This Terraform configuration defines the full pipeline infrastructure:
# - 5 S3 buckets (raw, processed, scripts, Athena results, Glue assets)
# - IAM role with least-privilege custom policy
# - 2 Glue databases (raw catalog, analytics catalog)
# - 1 Glue crawler (schema discovery)
# - 2 Glue catalog tables (enriched_sales, sales_summary)
# - 1 Glue ETL job (PySpark transformation)
# - Monitoring: SNS topic + EventBridge rules + CloudWatch alarm
#
# 
################################################################################

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state backend — production baseline state isolated from dev state
  backend "s3" {
    bucket  = "michel-project1-terraform-state-pipeline"
    key     = "production-baseline/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Project1-DataPipeline"
      Environment = "Production"
      Baseline    = "December2025"
      ManagedBy   = "Terraform"
    }
  }
}

################################################################################
# S3 BUCKETS — DATA LAKE STORAGE
################################################################################

# Bucket 1: Raw Data — stores input CSV and JSON files
resource "aws_s3_bucket" "raw_data" {
  bucket = "michel-raw-data-pipeline-project1"

  tags = {
    Name        = "Raw Data Bucket"
    Description = "Stores raw CSV and JSON input files for data pipeline"
    Layer       = "Ingestion"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_data" {
  bucket = aws_s3_bucket.raw_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Bucket 2: Processed Data — stores enriched Parquet output from Glue ETL
resource "aws_s3_bucket" "processed_data" {
  bucket = "michel-processed-data-pipeline-project1"

  tags = {
    Name        = "Processed Data Bucket"
    Description = "Stores enriched and aggregated data in Parquet format"
    Layer       = "Storage"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "processed_data" {
  bucket = aws_s3_bucket.processed_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Versioning enabled — protects against accidental deletion of processed data
resource "aws_s3_bucket_versioning" "processed_data" {
  bucket = aws_s3_bucket.processed_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Bucket 3: Glue Scripts — stores PySpark ETL script source
resource "aws_s3_bucket" "glue_scripts" {
  bucket = "michel-glue-scripts-pipeline-project1"

  tags = {
    Name        = "Glue Scripts Bucket"
    Description = "Stores Glue ETL job scripts"
    Layer       = "Compute"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "glue_scripts" {
  bucket = aws_s3_bucket.glue_scripts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Versioning enabled — protects against accidental deletion or overwrites of ETL scripts
resource "aws_s3_bucket_versioning" "glue_scripts" {
  bucket = aws_s3_bucket.glue_scripts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Bucket 4: Athena Query Results — stores query output and metadata
resource "aws_s3_bucket" "athena_results" {
  bucket = "michel-athena-results-project1-dec2025"

  tags = {
    Name        = "Athena Results Bucket"
    Description = "Stores Athena query results and metadata"
    Layer       = "Analytics"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Bucket 5: Glue Assets — AWS-managed bucket for Glue temporary files and Spark logs
resource "aws_s3_bucket" "glue_assets" {
  bucket = "aws-glue-assets-${var.aws_account_id}-${var.aws_region}"

  tags = {
    Name        = "AWS Glue Assets"
    Description = "AWS-managed bucket for Glue temporary files and Spark logs"
    Note        = "Auto-created by AWS Glue service"
    Layer       = "Compute"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "glue_assets" {
  bucket = aws_s3_bucket.glue_assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

################################################################################
# S3 BUCKET POLICIES — DEFENSE-IN-DEPTH
#
# These policies enforce encryption and HTTPS at the bucket level, providing
# protection independent of IAM. Even if IAM is misconfigured, these policies
# prevent unencrypted uploads and insecure (HTTP) connections.
################################################################################

resource "aws_s3_bucket_policy" "raw_data" {
  bucket = aws_s3_bucket.raw_data.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyUnencryptedObjectUploads"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.raw_data.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "AES256"
          }
        }
      },
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.raw_data.arn,
          "${aws_s3_bucket.raw_data.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_policy" "processed_data" {
  bucket = aws_s3_bucket.processed_data.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Note: DenyUnencryptedObjectUploads is intentionally NOT applied to this bucket.
      # The processed_data bucket is written by AWS Glue ETL, which does not include
      # the x-amz-server-side-encryption header in PutObject requests by default.
      # Bucket-level default encryption (SSE-S3 / AES256) is still enabled, ensuring
      # all objects are encrypted at rest. The raw_data and glue_scripts buckets,
      # which are written by CLI/manual processes, retain the stricter policy.
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.processed_data.arn,
          "${aws_s3_bucket.processed_data.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_policy" "glue_scripts" {
  bucket = aws_s3_bucket.glue_scripts.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyUnencryptedObjectUploads"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.glue_scripts.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "AES256"
          }
        }
      },
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.glue_scripts.arn,
          "${aws_s3_bucket.glue_scripts.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

################################################################################
# S3 PUBLIC ACCESS BLOCK — DEFENSE-IN-DEPTH
#
# Explicitly block all public access on every pipeline bucket. This operates
# at a separate layer from bucket policies — even if a bucket policy were
# accidentally misconfigured to allow public access, this block prevents it.
################################################################################

resource "aws_s3_bucket_public_access_block" "raw_data" {
  bucket                  = aws_s3_bucket.raw_data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "processed_data" {
  bucket                  = aws_s3_bucket.processed_data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "glue_scripts" {
  bucket                  = aws_s3_bucket.glue_scripts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket                  = aws_s3_bucket.athena_results.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "glue_assets" {
  bucket                  = aws_s3_bucket.glue_assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

################################################################################
# IAM ROLE — GLUE SERVICE ROLE
################################################################################

resource "aws_iam_role" "glue_service_role" {
  name        = "Glue-to-Access-S3-Role-December2025"
  description = "IAM role for AWS Glue to access pipeline S3 buckets and execute ETL jobs"

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

  tags = {
    Name = "Glue Service Role"
  }
}

# AWS-managed policy for Glue service operations (crawlers, ETL execution)
resource "aws_iam_role_policy_attachment" "glue_service_role_policy" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Custom least-privilege S3 policy — replaces overly-permissive AmazonS3FullAccess
# Grants Glue access to ONLY the 5 pipeline buckets, not all S3 in the account
resource "aws_iam_role_policy" "glue_s3_least_privilege" {
  name = "glue-pipeline-s3-access"
  role = aws_iam_role.glue_service_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowListSpecificBuckets"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.raw_data.arn,
          aws_s3_bucket.processed_data.arn,
          aws_s3_bucket.glue_scripts.arn,
          aws_s3_bucket.athena_results.arn,
          aws_s3_bucket.glue_assets.arn
        ]
      },
      {
        Sid    = "AllowReadWriteSpecificBuckets"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.raw_data.arn}/*",
          "${aws_s3_bucket.processed_data.arn}/*",
          "${aws_s3_bucket.glue_scripts.arn}/*",
          "${aws_s3_bucket.athena_results.arn}/*",
          "${aws_s3_bucket.glue_assets.arn}/*"
        ]
      }
    ]
  })
}

################################################################################
# GLUE DATA CATALOG — DATABASES
################################################################################

# Database for raw data — populated by crawler from S3 input files
resource "aws_glue_catalog_database" "sales_pipeline_db" {
  name        = "project1_sales_pipeline_db_december2025"
  description = "Database for raw sales and customer data discovered by Glue crawler"

  location_uri = "s3://${aws_s3_bucket.raw_data.id}/input/"

}

# Database for processed analytics tables — queried by Athena
resource "aws_glue_catalog_database" "sales_analytics_db" {
  name        = "project1_sales_analytics_db"
  description = "Database for processed analytics tables queried by Athena"

  location_uri = "s3://${aws_s3_bucket.processed_data.id}/"

}

################################################################################
# GLUE CRAWLER — SCHEMA DISCOVERY
################################################################################

resource "aws_glue_crawler" "sales_data_crawler" {
  name          = "project1-crawler-data-pipeline-sales-dec2025"
  role          = aws_iam_role.glue_service_role.arn
  database_name = aws_glue_catalog_database.sales_pipeline_db.name
  description   = "Project1 crawler — discovers schema from sales CSV and customer JSON in S3"

  s3_target {
    path = "s3://${aws_s3_bucket.raw_data.id}/input/"
  }

  recrawl_policy {
    recrawl_behavior = "CRAWL_EVERYTHING"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "DEPRECATE_IN_DATABASE"
  }

  lineage_configuration {
    crawler_lineage_settings = "DISABLE"
  }

  configuration = jsonencode({
    Version              = 1.0
    CreatePartitionIndex = true
  })

  tags = {
    Name = "Project1 Sales Data Crawler"
  }
}

################################################################################
# GLUE CATALOG TABLES — PROCESSED DATA
#
# Note: Raw tables (sales_data_csv, customer_demographics_json) are created
# automatically by the crawler. The two tables below are the processed-data
# tables created from the ETL job output (Parquet files in S3).
################################################################################

# Table 1: Enriched Sales — sales joined with customer demographics
resource "aws_glue_catalog_table" "enriched_sales" {
  name          = "enriched_sales"
  database_name = aws_glue_catalog_database.sales_analytics_db.name
  description   = "Enriched sales data — sales transactions joined with customer demographics"

  table_type = "EXTERNAL_TABLE"

  parameters = {
    "classification"      = "parquet"
    "compressionType"     = "snappy"
    "typeOfData"          = "file"
    "EXTERNAL"            = "TRUE"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.processed_data.id}/enriched/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "transaction_id"
      type = "string"
    }
    columns {
      name = "date"
      type = "string"
    }
    columns {
      name = "customer_id"
      type = "string"
    }
    columns {
      name = "product"
      type = "string"
    }
    columns {
      name = "quantity"
      type = "bigint"
    }
    columns {
      name = "unit_price"
      type = "double"
    }
    columns {
      name = "region"
      type = "string"
    }
    columns {
      name = "total_amount"
      type = "double"
    }
    columns {
      name = "age_group"
      type = "string"
    }
    columns {
      name = "membership_tier"
      type = "string"
    }
    columns {
      name = "signup_date"
      type = "string"
    }
    columns {
      name = "day"
      type = "bigint"
    }
  }

  partition_keys {
    name = "year"
    type = "bigint"
  }
  partition_keys {
    name = "month"
    type = "bigint"
  }
}

# Table 2: Sales Summary — pre-aggregated metrics for fast dashboard queries
resource "aws_glue_catalog_table" "sales_summary" {
  name          = "sales_summary"
  database_name = aws_glue_catalog_database.sales_analytics_db.name
  description   = "Pre-aggregated sales summary by region, product, year, and month"

  table_type = "EXTERNAL_TABLE"

  parameters = {
    "classification"      = "parquet"
    "compressionType"     = "snappy"
    "typeOfData"          = "file"
    "EXTERNAL"            = "TRUE"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.processed_data.id}/summary/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "region"
      type = "string"
    }
    columns {
      name = "product"
      type = "string"
    }
    columns {
      name = "year"
      type = "bigint"
    }
    columns {
      name = "month"
      type = "bigint"
    }
    columns {
      name = "total_revenue"
      type = "double"
    }
    columns {
      name = "transaction_count"
      type = "bigint"
    }
    columns {
      name = "avg_transaction_value"
      type = "double"
    }
  }
}

################################################################################
# GLUE ETL JOB — PYSPARK TRANSFORMATION
#
# Joins raw sales + customer data, partitions by year/month, writes Parquet.
# max_retries = 2 → automatic retry on transient failures (reliability).
################################################################################

resource "aws_glue_job" "project1_etl_pipeline" {
  name              = "glue-job-project1-etl-pipeline"
  description       = "ETL pipeline: joins sales + customer data, creates aggregated summaries, writes partitioned Parquet"
  role_arn          = aws_iam_role.glue_service_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  max_retries       = 2
  timeout           = 10
  execution_class   = "STANDARD"

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.glue_assets.id}/scripts/glue_etl_job.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-metrics"          = "true"
    "--enable-job-insights"     = "true"
    "--enable-glue-datacatalog" = "true"
    "--job-bookmark-option"     = "job-bookmark-disable"
    "--job-language"            = "python"
    "--spark-event-logs-path"   = "s3://${aws_s3_bucket.glue_assets.id}/sparkHistoryLogs/"
    "--TempDir"                 = "s3://${aws_s3_bucket.glue_assets.id}/temporary/"
    "--enable-spark-ui"         = "true"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  tags = {
    Name = "Project1 Sales ETL Pipeline"
  }
}

################################################################################
# MONITORING — SNS TOPIC + EVENTBRIDGE RULES + CLOUDWATCH ALARM
#
# Three alarms cover the pipeline's primary failure modes:
#   1. Glue Job Failure       → EventBridge rule on job state change
#   2. Glue Job Duration > 10 min → CloudWatch metric alarm
#   3. Glue Crawler Failure   → EventBridge rule on crawler state change
#
# All alarms publish to the same SNS topic, which emails the configured address.
################################################################################

# SNS topic — receives all pipeline failure notifications
resource "aws_sns_topic" "pipeline_alerts" {
  name         = "project1-pipeline-alerts"
  display_name = "Project1 Data Pipeline Alerts"

  tags = {
    Name = "Pipeline Alerts Topic"
  }
}

# Email subscription — confirmation email sent to alert_email address on apply
resource "aws_sns_topic_subscription" "pipeline_email_alerts" {
  topic_arn = aws_sns_topic.pipeline_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Topic policy — allows EventBridge and CloudWatch Alarms to publish to this topic
resource "aws_sns_topic_policy" "pipeline_alerts" {
  arn = aws_sns_topic.pipeline_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEventBridgePublish"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sns:Publish"
        Resource = aws_sns_topic.pipeline_alerts.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = [
              aws_cloudwatch_event_rule.glue_job_failures.arn,
              aws_cloudwatch_event_rule.glue_crawler_failures.arn
            ]
          }
        }
      },
      {
        Sid    = "AllowCloudWatchAlarmsPublish"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action   = "sns:Publish"
        Resource = aws_sns_topic.pipeline_alerts.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_cloudwatch_metric_alarm.glue_job_duration.arn
          }
        }
      }
    ]
  })
}

# --- ALARM 1: Glue Job Failure ---

resource "aws_cloudwatch_event_rule" "glue_job_failures" {
  name        = "project1-glue-job-failures"
  description = "Triggers when the sales ETL Glue job transitions to FAILED or TIMEOUT"

  event_pattern = jsonencode({
    source      = ["aws.glue"]
    detail-type = ["Glue Job State Change"]
    detail = {
      jobName = [aws_glue_job.project1_etl_pipeline.name]
      state   = ["FAILED", "TIMEOUT"]
    }
  })

  tags = {
    Name = "Glue Job Failure Detection"
  }
}

resource "aws_cloudwatch_event_target" "glue_job_failures_sns" {
  rule      = aws_cloudwatch_event_rule.glue_job_failures.name
  target_id = "SendGlueJobFailureToSNS"
  arn       = aws_sns_topic.pipeline_alerts.arn
}

# --- ALARM 2: Glue Job Duration ---

resource "aws_cloudwatch_metric_alarm" "glue_job_duration" {
  alarm_name          = "project1-glue-job-duration-exceeded"
  alarm_description   = "Glue ETL job duration exceeded 10 minutes — investigate for performance degradation"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "glue.driver.aggregate.elapsedTime"
  namespace           = "Glue"
  period              = 300
  statistic           = "Average"
  threshold           = 600000 # 10 minutes in milliseconds
  alarm_actions       = [aws_sns_topic.pipeline_alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    JobName = aws_glue_job.project1_etl_pipeline.name
    Type    = "gauge"
  }

  tags = {
    Name = "Glue Job Duration Alarm"
  }
}

# --- ALARM 3: Glue Crawler Failure ---

resource "aws_cloudwatch_event_rule" "glue_crawler_failures" {
  name        = "project1-glue-crawler-failures"
  description = "Triggers when the sales data Glue crawler fails"

  event_pattern = jsonencode({
    source      = ["aws.glue"]
    detail-type = ["Glue Crawler State Change"]
    detail = {
      crawlerName = [aws_glue_crawler.sales_data_crawler.name]
      state       = ["Failed"]
    }
  })

  tags = {
    Name = "Glue Crawler Failure Detection"
  }
}

resource "aws_cloudwatch_event_target" "glue_crawler_failures_sns" {
  rule      = aws_cloudwatch_event_rule.glue_crawler_failures.name
  target_id = "SendGlueCrawlerFailureToSNS"
  arn       = aws_sns_topic.pipeline_alerts.arn
}

################################################################################
# CLOUDWATCH LOGS — AUTO-CREATED BY GLUE
#
# AWS Glue automatically creates the following CloudWatch log groups when jobs
# and crawlers run. No Terraform configuration is required for log creation:
#
#   /aws-glue/jobs/output    — Glue job stdout logs
#   /aws-glue/jobs/error     — Glue job stderr logs
#   /aws-glue/crawlers       — Crawler execution logs
#
# To view logs:
#   AWS Console → CloudWatch → Log Groups → search for job or crawler name
#
# Cost: AWS Free Tier includes 5 GB of log ingestion + storage per month.
# Default retention: 30 days (configurable if needed).
################################################################################
