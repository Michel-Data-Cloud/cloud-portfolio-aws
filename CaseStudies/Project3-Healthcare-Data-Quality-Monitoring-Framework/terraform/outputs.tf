output "input_bucket_name" {
  description = "S3 bucket for raw patient data input"
  value       = aws_s3_bucket.patient_data_input.bucket
}

output "input_bucket_arn" {
  description = "ARN of the patient data input bucket"
  value       = aws_s3_bucket.patient_data_input.arn
}

output "results_bucket_name" {
  description = "S3 bucket for quality check results"
  value       = aws_s3_bucket.patient_quality_results.bucket
}

output "results_bucket_arn" {
  description = "ARN of the quality results bucket"
  value       = aws_s3_bucket.patient_quality_results.arn
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.patient_data_quality_lambda_role.arn
}

output "lambda_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.patient_data_quality_lambda_role.name
}

output "quality_engine_function_name" {
  description = "Name of the patient data quality Lambda function"
  value       = aws_lambda_function.quality_engine.function_name
}

output "quality_engine_function_arn" {
  description = "ARN of the patient data quality Lambda function"
  value       = aws_lambda_function.quality_engine.arn
}

output "quality_engine_log_group" {
  description = "CloudWatch log group for the quality engine Lambda"
  value       = aws_cloudwatch_log_group.quality_engine_logs.name
}

output "sns_topic_arn" {
  description = "ARN of the patient data quality alerts SNS topic"
  value       = aws_sns_topic.quality_alerts.arn
}

output "sns_topic_name" {
  description = "Name of the SNS alerts topic"
  value       = aws_sns_topic.quality_alerts.name
}

output "alarm_low_quality_score" {
  description = "CloudWatch alarm name for low quality score"
  value       = aws_cloudwatch_metric_alarm.low_quality_score.alarm_name
}

output "alarm_critical_issues" {
  description = "CloudWatch alarm name for critical issues"
  value       = aws_cloudwatch_metric_alarm.critical_issues.alarm_name
}

output "alarm_duplicate_mrns" {
  description = "CloudWatch alarm name for duplicate MRNs"
  value       = aws_cloudwatch_metric_alarm.duplicate_mrns.alarm_name
}

output "cloudwatch_dashboard_url" {
  description = "URL to the patient data quality CloudWatch dashboard"
  value       = "https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=project3-patient-data-quality-dashboard"
}

output "eventbridge_schedule_name" {
  description = "Name of the EventBridge scheduled quality check"
  value       = aws_scheduler_schedule.patient_data_quality_daily.name
}

output "eventbridge_schedule_expression" {
  description = "Cron expression for the scheduled quality check"
  value       = aws_scheduler_schedule.patient_data_quality_daily.schedule_expression
}
