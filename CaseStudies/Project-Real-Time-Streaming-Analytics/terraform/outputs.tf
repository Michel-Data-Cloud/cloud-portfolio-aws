# =============================================================================
# OUTPUTS
# These print useful resource info after `terraform apply` runs.
# You can also reference these in CI/CD pipelines or other Terraform modules.
# =============================================================================

# -----------------------------------------------------------------------------
# Account & Region
# -----------------------------------------------------------------------------

output "aws_account_id" {
  description = "The AWS account ID resources are deployed into"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "The AWS region resources are deployed into"
  value       = data.aws_region.current.name
}

# -----------------------------------------------------------------------------
# Kinesis
# -----------------------------------------------------------------------------

output "kinesis_stream_name" {
  description = "Name of the Kinesis Data Stream"
  value       = aws_kinesis_stream.sensor_stream.name
}

output "kinesis_stream_arn" {
  description = "ARN of the Kinesis Data Stream"
  value       = aws_kinesis_stream.sensor_stream.arn
}

# -----------------------------------------------------------------------------
# DynamoDB
# -----------------------------------------------------------------------------

output "dynamodb_table_name" {
  description = "Name of the DynamoDB sensor readings table"
  value       = aws_dynamodb_table.sensor_readings.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB sensor readings table"
  value       = aws_dynamodb_table.sensor_readings.arn
}

# -----------------------------------------------------------------------------
# Lambda
# -----------------------------------------------------------------------------

output "processor_lambda_name" {
  description = "Name of the Kinesis stream processor Lambda function"
  value       = aws_lambda_function.stream_processor.function_name
}

output "aggregator_lambda_name" {
  description = "Name of the aggregation Lambda function"
  value       = aws_lambda_function.stream_aggregator.function_name
}

# -----------------------------------------------------------------------------
# SNS
# -----------------------------------------------------------------------------

output "sns_topic_arn" {
  description = "ARN of the SNS anomaly alert topic"
  value       = aws_sns_topic.anomaly_alerts.arn
}

# -----------------------------------------------------------------------------
# CloudWatch
# -----------------------------------------------------------------------------

output "cloudwatch_dashboard_url" {
  description = "Direct URL to the CloudWatch dashboard in the AWS console"
  value       = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.streaming_dashboard.dashboard_name}"
}
