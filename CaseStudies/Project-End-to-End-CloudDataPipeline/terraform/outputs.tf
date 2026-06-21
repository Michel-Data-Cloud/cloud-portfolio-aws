################################################################################
# PROJECT 1 — END-TO-END AWS DATA PIPELINE
# Terraform Outputs
################################################################################

# --- Account & Region ---

output "aws_account_id" {
  description = "AWS account ID where resources are deployed"
  value       = var.aws_account_id
}

output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = var.aws_region
}

# --- S3 Buckets ---

output "s3_bucket_raw_data" {
  description = "S3 bucket for raw input data (CSV, JSON)"
  value       = aws_s3_bucket.raw_data.id
}

output "s3_bucket_processed_data" {
  description = "S3 bucket for processed/enriched Parquet data"
  value       = aws_s3_bucket.processed_data.id
}

output "s3_bucket_glue_scripts" {
  description = "S3 bucket for Glue ETL scripts"
  value       = aws_s3_bucket.glue_scripts.id
}

output "s3_bucket_athena_results" {
  description = "S3 bucket for Athena query results"
  value       = aws_s3_bucket.athena_results.id
}

output "s3_bucket_glue_assets" {
  description = "AWS-managed S3 bucket for Glue temporary files and Spark logs"
  value       = aws_s3_bucket.glue_assets.id
}

# --- Glue Resources ---

output "glue_database_raw" {
  description = "Glue Data Catalog database for raw data"
  value       = aws_glue_catalog_database.sales_pipeline_db.name
}

output "glue_database_analytics" {
  description = "Glue Data Catalog database for processed analytics data"
  value       = aws_glue_catalog_database.sales_analytics_db.name
}

output "glue_crawler_name" {
  description = "Glue crawler that discovers schema from raw S3 data"
  value       = aws_glue_crawler.sales_data_crawler.name
}

output "glue_job_name" {
  description = "Glue ETL job that transforms and enriches sales data"
  value       = aws_glue_job.project1_etl_pipeline.name
}

# --- IAM ---

output "iam_role_name" {
  description = "IAM role name used by Glue crawler and ETL job"
  value       = aws_iam_role.glue_service_role.name
}

# --- Monitoring ---

output "sns_topic_arn" {
  description = "SNS topic ARN for pipeline failure alerts"
  value       = aws_sns_topic.pipeline_alerts.arn
}

output "eventbridge_rule_job_failure" {
  description = "EventBridge rule that detects Glue job FAILED or TIMEOUT states"
  value       = aws_cloudwatch_event_rule.glue_job_failures.name
}

output "cloudwatch_alarm_job_duration" {
  description = "CloudWatch alarm that fires when Glue job duration exceeds 10 minutes"
  value       = aws_cloudwatch_metric_alarm.glue_job_duration.alarm_name
}

output "eventbridge_rule_crawler_failure" {
  description = "EventBridge rule that detects Glue crawler Failed state"
  value       = aws_cloudwatch_event_rule.glue_crawler_failures.name
}
