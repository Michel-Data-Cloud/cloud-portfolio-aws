################################################################################
# OUTPUTS FOR PROJECT1 DECEMBER 2025 BASELINE
################################################################################

################################################################################
# S3 BUCKET OUTPUTS
################################################################################

output "raw_data_bucket_name" {
  description = "Name of the S3 bucket storing raw input data"
  value       = aws_s3_bucket.raw_data.id
}

output "raw_data_bucket_arn" {
  description = "ARN of the raw data S3 bucket"
  value       = aws_s3_bucket.raw_data.arn
}

output "processed_data_bucket_name" {
  description = "Name of the S3 bucket storing processed data"
  value       = aws_s3_bucket.processed_data.id
}

output "processed_data_bucket_arn" {
  description = "ARN of the processed data S3 bucket"
  value       = aws_s3_bucket.processed_data.arn
}

output "glue_scripts_bucket_name" {
  description = "Name of the S3 bucket storing Glue scripts"
  value       = aws_s3_bucket.glue_scripts.id
}

output "athena_results_bucket_name" {
  description = "Name of the S3 bucket storing Athena query results"
  value       = aws_s3_bucket.athena_results.id
}

output "glue_assets_bucket_name" {
  description = "Name of the AWS-managed Glue assets bucket"
  value       = aws_s3_bucket.glue_assets.id
}

################################################################################
# GLUE DATABASE OUTPUTS
################################################################################

output "raw_database_name" {
  description = "Name of the Glue database for raw data"
  value       = aws_glue_catalog_database.sales_pipeline_db.name
}

output "raw_database_location" {
  description = "S3 location of the raw data database"
  value       = aws_glue_catalog_database.sales_pipeline_db.location_uri
}

output "analytics_database_name" {
  description = "Name of the Glue database for analytics"
  value       = aws_glue_catalog_database.sales_analytics_db.name
}

output "analytics_database_location" {
  description = "S3 location of the analytics database"
  value       = aws_glue_catalog_database.sales_analytics_db.location_uri
}

################################################################################
# GLUE CRAWLER OUTPUTS
################################################################################

output "crawler_name" {
  description = "Name of the Glue crawler"
  value       = aws_glue_crawler.sales_data_crawler.name
}

output "crawler_arn" {
  description = "ARN of the Glue crawler"
  value       = aws_glue_crawler.sales_data_crawler.arn
}

################################################################################
# GLUE JOB OUTPUTS
################################################################################

output "etl_job_name" {
  description = "Name of the Glue ETL job"
  value       = aws_glue_job.sales_etl_pipeline.name
}

output "etl_job_arn" {
  description = "ARN of the Glue ETL job"
  value       = aws_glue_job.sales_etl_pipeline.arn
}

output "etl_job_script_location" {
  description = "S3 location of the ETL job script"
  value       = aws_glue_job.sales_etl_pipeline.command[0].script_location
}

################################################################################
# IAM ROLE OUTPUTS
################################################################################

output "glue_role_name" {
  description = "Name of the IAM role for Glue"
  value       = aws_iam_role.glue_service_role.name
}

output "glue_role_arn" {
  description = "ARN of the IAM role for Glue"
  value       = aws_iam_role.glue_service_role.arn
}

################################################################################
# GLUE TABLE OUTPUTS
################################################################################

output "enriched_sales_table" {
  description = "Name of the enriched sales table"
  value       = aws_glue_catalog_table.enriched_sales.name
}

output "sales_summary_table" {
  description = "Name of the sales summary table"
  value       = aws_glue_catalog_table.sales_summary.name
}

################################################################################
# SUMMARY OUTPUT
################################################################################

output "infrastructure_summary" {
  description = "Summary of the December 2025 baseline infrastructure"
  value = {
    region              = var.aws_region
    s3_buckets          = 5
    glue_databases      = 2
    glue_crawlers       = 1
    glue_jobs           = 1
    glue_tables_defined = 2
    iam_roles           = 1
    baseline_date       = var.baseline_date
  }
}
