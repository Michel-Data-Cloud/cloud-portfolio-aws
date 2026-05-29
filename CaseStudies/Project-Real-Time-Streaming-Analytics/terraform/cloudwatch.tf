# =============================================================================
# CLOUDWATCH — Log Groups, Alarms, and Dashboard
# =============================================================================
# Purpose : Full observability layer for the streaming pipeline.
#           Covers structured logging, automated alerting, and a real-time
#           visual dashboard.
#
# Resources:
#   1. Log Groups    — Explicit CloudWatch Logs groups for both Lambdas
#   2. Alarms (4)    — Automated alerts on pipeline health metrics
#   3. Dashboard     — Real-time visualization of the full pipeline
#
# Well-Architected:
#   - Observability : Logs + metrics + alarms + dashboard = full observability
#                     at every layer of the pipeline.
#   - Reliability   : Alarms notify before problems become outages.
#   - Cost          : Log retention set to 30 days (configurable).
#                     Dashboard: $3/month flat fee.
#                     Alarms: $0.10/alarm/month.
# =============================================================================


# =============================================================================
# LOG GROUPS
# =============================================================================
# Explicit log groups give us control over retention and prevent the default
# behaviour where Lambda creates log groups with infinite retention.
# Infinite retention = unbounded CloudWatch Logs storage cost.

resource "aws_cloudwatch_log_group" "processor_logs" {
  name              = "/aws/lambda/${var.project_name}-stream-processor"
  retention_in_days = 30   # Balance debuggability vs. cost
  # Production enhancement: set to 90 or 365 for compliance requirements

  tags = {
    Name = "${var.project_name}-processor-logs"
  }
}

resource "aws_cloudwatch_log_group" "aggregator_logs" {
  name              = "/aws/lambda/${var.project_name}-stream-aggregator"
  retention_in_days = 30

  tags = {
    Name = "${var.project_name}-aggregator-logs"
  }
}


# =============================================================================
# CLOUDWATCH ALARMS
# =============================================================================
# All alarms route to the SNS topic for email delivery.
# Alarm design principle: alert on symptoms the operations team can act on,
# not on internal implementation details.

# -----------------------------------------------------------------------------
# Alarm 1 — Processor Lambda Errors
# Fires immediately when the stream processor has any invocation error.
# Any error here means sensor data is not reaching DynamoDB.
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "processor_errors" {
  alarm_name          = "${var.project_name}-processor-errors"
  alarm_description   = "Fires when the stream processor Lambda has any invocation errors. Sensor data may not be reaching DynamoDB."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  threshold           = 1
  treat_missing_data  = "notBreaching"   # No data = no error (sparse metric)

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  statistic   = "Sum"
  period      = 60   # 1-minute evaluation window

  dimensions = {
    FunctionName = aws_lambda_function.stream_processor.function_name
  }

  alarm_actions = [aws_sns_topic.anomaly_alerts.arn]
  ok_actions    = [aws_sns_topic.anomaly_alerts.arn]   # Notify when alarm clears too

  tags = {
    Name = "${var.project_name}-processor-errors"
  }
}

# -----------------------------------------------------------------------------
# Alarm 2 — Aggregator Lambda Errors
# Fires when the aggregator has any invocation error.
# Any error here means CloudWatch metrics and anomaly alerts are not firing.
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "aggregator_errors" {
  alarm_name          = "${var.project_name}-aggregator-errors"
  alarm_description   = "Fires when the aggregator Lambda has any invocation errors. CloudWatch metrics and SNS anomaly alerts may not be publishing."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  threshold           = 1
  treat_missing_data  = "notBreaching"

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  statistic   = "Sum"
  period      = 60

  dimensions = {
    FunctionName = aws_lambda_function.stream_aggregator.function_name
  }

  alarm_actions = [aws_sns_topic.anomaly_alerts.arn]
  ok_actions    = [aws_sns_topic.anomaly_alerts.arn]

  tags = {
    Name = "${var.project_name}-aggregator-errors"
  }
}

# -----------------------------------------------------------------------------
# Alarm 3 — Kinesis Iterator Age (Consumer Lag)
# Measures how far behind the Lambda consumer is in reading the stream.
# A growing iterator age means the processor cannot keep up with ingest.
# Threshold: 60,000ms (60 seconds) — healthy pipeline should be near 0.
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "kinesis_iterator_age" {
  alarm_name          = "${var.project_name}-kinesis-iterator-age"
  alarm_description   = "Fires when the Lambda Kinesis consumer is more than 60 seconds behind the stream. Indicates the processor cannot keep up with ingest rate."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3    # Must breach for 3 consecutive periods to reduce noise
  threshold           = 60000
  treat_missing_data  = "notBreaching"

  namespace   = "AWS/Kinesis"
  metric_name = "GetRecords.IteratorAgeMilliseconds"
  statistic   = "Maximum"   # Worst-case lag, not average
  period      = 300         # 5-minute evaluation window

  dimensions = {
    StreamName = aws_kinesis_stream.sensor_stream.name
  }

  alarm_actions = [aws_sns_topic.anomaly_alerts.arn]
  ok_actions    = [aws_sns_topic.anomaly_alerts.arn]

  tags = {
    Name = "${var.project_name}-kinesis-iterator-age"
  }
}

# -----------------------------------------------------------------------------
# Alarm 4 — DynamoDB Write Latency
# Monitors PutItem latency as a leading indicator of DynamoDB health.
# High latency before hard errors — this alarm gives early warning.
# Note: DynamoDB SystemErrors not used because sparse metrics don't appear
# in CloudWatch until they fire. SuccessfulRequestLatency is a better
# leading indicator for proactive monitoring.
# Threshold: 100ms — healthy DynamoDB PutItem is typically 1–10ms.
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "dynamodb_write_latency" {
  alarm_name          = "${var.project_name}-dynamodb-write-latency"
  alarm_description   = "Fires when DynamoDB PutItem average latency exceeds 100ms. Indicates throttling, hot partition, or service degradation. Healthy latency is 1-10ms."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 100
  treat_missing_data  = "notBreaching"

  namespace   = "AWS/DynamoDB"
  metric_name = "SuccessfulRequestLatency"
  statistic   = "Average"
  period      = 300

  dimensions = {
    TableName = aws_dynamodb_table.sensor_readings.name
    Operation = "PutItem"
  }

  alarm_actions = [aws_sns_topic.anomaly_alerts.arn]
  ok_actions    = [aws_sns_topic.anomaly_alerts.arn]

  tags = {
    Name = "${var.project_name}-dynamodb-write-latency"
  }
}


# =============================================================================
# CLOUDWATCH DASHBOARD
# =============================================================================
# Single-pane-of-glass view of the entire pipeline.
# Pre-built with metric definitions so it populates automatically when
# data flows — no manual widget configuration needed after deployment.
#
# Layout (each row = 6 units tall, full width = 24 units):
#   Row 1: Kinesis Records (left) | Lambda Invocations/Errors (right)
#   Row 2: Lambda Duration (left) | DynamoDB Write Capacity (right)
#   Row 3: Sensor Temperature — all 4 sensors (full width)
#   Row 4: Pipeline Health Alarm Status (full width)

resource "aws_cloudwatch_dashboard" "streaming_dashboard" {
  dashboard_name = "${var.project_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [

      # -----------------------------------------------------------------------
      # Widget 1: Kinesis Incoming Records
      # Shows data ingestion rate — how many records/min are entering the stream
      # -----------------------------------------------------------------------
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Kinesis — Incoming Records/min"
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          period  = 60
          metrics = [
            [
              "AWS/Kinesis",
              "IncomingRecords",
              "StreamName",
              aws_kinesis_stream.sensor_stream.name,
              { stat = "Sum", period = 60 }
            ]
          ]
        }
      },

      # -----------------------------------------------------------------------
      # Widget 2: Processor Lambda Invocations vs Errors
      # Shows processing health — invocations should be steady, errors zero
      # -----------------------------------------------------------------------
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Processor Lambda — Invocations vs Errors"
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          period  = 60
          metrics = [
            [
              "AWS/Lambda", "Invocations", "FunctionName",
              aws_lambda_function.stream_processor.function_name,
              { stat = "Sum", period = 60 }
            ],
            [
              "AWS/Lambda", "Errors", "FunctionName",
              aws_lambda_function.stream_processor.function_name,
              { stat = "Sum", period = 60, color = "#d62728" }
            ]
          ]
        }
      },

      # -----------------------------------------------------------------------
      # Widget 3: Lambda Duration — both functions
      # Shows execution performance — rising duration could indicate
      # DynamoDB latency or Lambda cold start issues
      # -----------------------------------------------------------------------
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "Lambda Duration (ms) — Processor + Aggregator"
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          period  = 60
          metrics = [
            [
              "AWS/Lambda", "Duration", "FunctionName",
              aws_lambda_function.stream_processor.function_name,
              { stat = "Average", period = 60 }
            ],
            [
              "AWS/Lambda", "Duration", "FunctionName",
              aws_lambda_function.stream_aggregator.function_name,
              { stat = "Average", period = 60 }
            ]
          ]
        }
      },

      # -----------------------------------------------------------------------
      # Widget 4: DynamoDB Consumed Write Capacity
      # Shows database write load — spike indicates high ingest rate
      # -----------------------------------------------------------------------
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "DynamoDB — Consumed Write Capacity"
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          period  = 60
          metrics = [
            [
              "AWS/DynamoDB",
              "ConsumedWriteCapacityUnits",
              "TableName",
              aws_dynamodb_table.sensor_readings.name,
              { stat = "Sum", period = 60 }
            ]
          ]
        }
      },

      # -----------------------------------------------------------------------
      # Widget 5: Sensor Average Temperature — all 4 sensors
      # The key business metric — what the operations team actually monitors.
      # Published by the aggregator Lambda every 60 seconds.
      # -----------------------------------------------------------------------
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 24
        height = 6
        properties = {
          title   = "Sensor Avg Temperature — All Sensors (5-min window)"
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          period  = 60
          metrics = [
            [
              "StreamingAnalytics/Sensors", "AvgTemperature",
              "SensorId", "sensor-floor-A-01",
              { stat = "Average", period = 60 }
            ],
            [
              "StreamingAnalytics/Sensors", "AvgTemperature",
              "SensorId", "sensor-floor-A-02",
              { stat = "Average", period = 60 }
            ],
            [
              "StreamingAnalytics/Sensors", "AvgTemperature",
              "SensorId", "sensor-floor-B-01",
              { stat = "Average", period = 60 }
            ],
            [
              "StreamingAnalytics/Sensors", "AvgTemperature",
              "SensorId", "sensor-floor-B-02",
              { stat = "Average", period = 60 }
            ]
          ]
        }
      },

      # -----------------------------------------------------------------------
      # Widget 6: Pipeline Health — Alarm Status Panel
      # At-a-glance RAG (Red/Amber/Green) status of all 4 pipeline alarms.
      # First thing an ops engineer checks when responding to a page.
      # -----------------------------------------------------------------------
      {
        type   = "alarm"
        x      = 0
        y      = 18
        width  = 24
        height = 4
        properties = {
          title  = "Pipeline Health — All Alarms"
          alarms = [
            aws_cloudwatch_metric_alarm.processor_errors.arn,
            aws_cloudwatch_metric_alarm.aggregator_errors.arn,
            aws_cloudwatch_metric_alarm.kinesis_iterator_age.arn,
            aws_cloudwatch_metric_alarm.dynamodb_write_latency.arn,
          ]
        }
      }
    ]
  })
}
