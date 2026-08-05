# =============================================================================
# LAMBDA FUNCTIONS — Stream Processor + Stream Aggregator
# =============================================================================
# Purpose : Define both Lambda functions, their deployment packages,
#           environment variables, triggers, and CloudWatch log groups.
#
# Functions:
#   1. stream-processor  — Reads Kinesis → Enriches → Writes DynamoDB
#      Trigger: Kinesis event source mapping (batch=100, window=10s)
#
#   2. stream-aggregator — Queries DynamoDB → Aggregates → CloudWatch + SNS
#      Trigger: EventBridge scheduled rule (rate = 1 minute)
#
# Deployment Package:
#   Terraform uses the archive_file data source to zip each Lambda's
#   source directory and upload it on every apply. In production, a
#   CI/CD pipeline (GitHub Actions, CodePipeline) would handle packaging
#   and deployment separately from infrastructure changes.
#
# Well-Architected:
#   - Reliability  : Per-record error handling in processor prevents one
#                    bad record from blocking the entire batch.
#   - Security     : No hardcoded credentials. IAM roles handle all auth.
#                    Sensitive config in environment variables.
#   - Cost         : 256MB memory right-sized for these workloads.
#                    Lambda free tier covers 1M requests + 400K GB-sec/month.
#   - Performance  : Kinesis batch window of 10s accumulates records before
#                    invocation — more efficient than per-record invocation.
# =============================================================================


# -----------------------------------------------------------------------------
# DEPLOYMENT PACKAGES — Zip Lambda source directories
# -----------------------------------------------------------------------------

# Zip the processor Lambda source directory
data "archive_file" "processor_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/processor"
  output_path = "${path.module}/../lambda/processor.zip"
}

# Zip the aggregator Lambda source directory
data "archive_file" "aggregator_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/aggregator"
  output_path = "${path.module}/../lambda/aggregator.zip"
}


# =============================================================================
# FUNCTION 1 — Stream Processor
# Trigger  : Kinesis Data Stream event source mapping
# Role     : streaming-analytics-processor-role
# =============================================================================

resource "aws_lambda_function" "stream_processor" {
  function_name = "${var.project_name}-stream-processor"
  description   = "Reads IoT sensor records from Kinesis, enriches them with status and TTL, and writes to DynamoDB. Triggered by Kinesis event source mapping."
  role          = aws_iam_role.processor_role.arn
  runtime       = var.lambda_runtime
  handler       = "handler.lambda_handler"
  timeout       = var.lambda_timeout_seconds
  memory_size   = var.lambda_memory_mb

  # Deployment package — source hash ensures Lambda updates when code changes
  filename         = data.archive_file.processor_zip.output_path
  source_code_hash = data.archive_file.processor_zip.output_base64sha256

  # Environment variables — no hardcoded values in source code
  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.sensor_readings.name
      # Processor does not need SNS or anomaly threshold —
      # those belong to the aggregator. Least privilege applies
      # to config as well as permissions.
    }
  }

  # CloudWatch Logs configuration
  # Log group is created explicitly below for lifecycle control
  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.processor_logs.name
  }

  # Dead Letter Queue — captures failed invocation payloads for reprocessing
  # Note: Kinesis-triggered Lambdas handle failures via the event source
  # mapping's bisect_batch_on_function_error and destination_config.
  # A standard DLQ is not applicable here; see event source mapping below.

  depends_on = [
    aws_iam_role_policy_attachment.processor_policy_attachment,
    aws_cloudwatch_log_group.processor_logs,
  ]

  tags = {
    Name = "${var.project_name}-stream-processor"
  }
}

# Kinesis Event Source Mapping — connects the stream to the processor Lambda
resource "aws_lambda_event_source_mapping" "kinesis_processor_trigger" {
  event_source_arn  = aws_kinesis_stream.sensor_stream.arn
  function_name     = aws_lambda_function.stream_processor.arn
  starting_position = "TRIM_HORIZON"

  # Batch configuration
  # batch_size    : Max records per Lambda invocation (1–10,000)
  # maximum_batching_window_in_seconds: # Accumulate records for up to 10 seconds before invoking Lambda
  # This reduces Lambda invocations and improves efficiency.
  batch_size                         = var.processor_batch_size
  maximum_batching_window_in_seconds         = 10   # ← FIXED
  bisect_batch_on_function_error     = true   # On error, split batch in half to isolate bad record
  maximum_retry_attempts             = 3       # Retry failed batches up to 3 times

  # Destination for failed records after all retries are exhausted
  # Points to an SQS Dead Letter Queue for manual inspection/replay
  # Note: SQS DLQ resource is listed in enhancements — uncomment when added
  # destination_config {
  #   on_failure {
  #     destination_arn = aws_sqs_queue.processor_dlq.arn
  #   }
  # }

  depends_on = [aws_iam_role_policy_attachment.processor_policy_attachment]
}


# =============================================================================
# FUNCTION 2 — Stream Aggregator
# Trigger  : EventBridge scheduled rule (every 1 minute)
# Role     : streaming-analytics-aggregator-role
# =============================================================================

resource "aws_lambda_function" "stream_aggregator" {
  function_name = "${var.project_name}-stream-aggregator"
  description   = "Runs every 60 seconds. Queries DynamoDB for 5-min windowed sensor data, computes avg/min/max, publishes CloudWatch metrics, and sends SNS alerts on anomalies."
  role          = aws_iam_role.aggregator_role.arn
  runtime       = var.lambda_runtime
  handler       = "handler.lambda_handler"
  timeout       = var.lambda_timeout_seconds
  memory_size   = var.lambda_memory_mb

  filename         = data.archive_file.aggregator_zip.output_path
  source_code_hash = data.archive_file.aggregator_zip.output_base64sha256

  environment {
    variables = {
      TABLE_NAME          = aws_dynamodb_table.sensor_readings.name
      SNS_TOPIC_ARN       = aws_sns_topic.anomaly_alerts.arn
      ANOMALY_THRESHOLD   = tostring(var.anomaly_threshold)
      WINDOW_MINUTES      = "5"
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.aggregator_logs.name
  }

  depends_on = [
    aws_iam_role_policy_attachment.aggregator_policy_attachment,
    aws_cloudwatch_log_group.aggregator_logs,
  ]

  tags = {
    Name = "${var.project_name}-stream-aggregator"
  }
}

# EventBridge Rule — fires the aggregator Lambda every 60 seconds
resource "aws_cloudwatch_event_rule" "aggregator_schedule" {
  name                = "${var.project_name}-aggregator-schedule"
  description         = "Triggers the stream aggregator Lambda every 60 seconds to compute windowed sensor aggregations."
  schedule_expression = "rate(1 minute)"
  state               = "ENABLED"

  tags = {
    Name = "${var.project_name}-aggregator-schedule"
  }
}

# EventBridge Target — points the rule at the aggregator Lambda
resource "aws_cloudwatch_event_target" "aggregator_target" {
  rule      = aws_cloudwatch_event_rule.aggregator_schedule.name
  target_id = "StreamAggregatorTarget"
  arn       = aws_lambda_function.stream_aggregator.arn
}

# Lambda Permission — allows EventBridge to invoke the aggregator function
resource "aws_lambda_permission" "allow_eventbridge_aggregator" {
  statement_id  = "AllowEventBridgeInvokeAggregator"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stream_aggregator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.aggregator_schedule.arn
}
