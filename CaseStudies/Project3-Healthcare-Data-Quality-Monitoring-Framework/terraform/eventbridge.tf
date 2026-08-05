# --- EventBridge Scheduler IAM Role ---
# Auto-created by the console when we created the schedule.
# Defined here so Terraform tracks it and can manage it.
resource "aws_iam_role" "eventbridge_scheduler_role" {
  name        = "Amazon_EventBridge_Scheduler_LAMBDA_a444f2f3f9"
  description = "Execution role for EventBridge Scheduler to invoke patient data quality Lambda"
  path        = "/service-role/"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "scheduler.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "eventbridge_scheduler_policy" {
  name = "EventBridgeSchedulerLambdaInvokePolicy"
  role = aws_iam_role.eventbridge_scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.quality_engine.arn
      }
    ]
  })
}

# --- EventBridge Scheduler Schedule ---
# Fires daily at 2:05 AM UTC — 5 minutes after the hospital's
# nightly EHR batch export completes at 2:00 AM UTC.
# Gives the data team a quality report before clinical staff
# arrive at 7:00 AM.
resource "aws_scheduler_schedule" "patient_data_quality_daily" {
  name        = "project3-patient-data-quality-scheduled-check-rule"
  description = "Daily scheduled trigger for patient data quality engine — validates nightly EHR batch exports"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "cron(5 2 * * ? *)"

  target {
    arn      = aws_lambda_function.quality_engine.arn
    role_arn = aws_iam_role.eventbridge_scheduler_role.arn

    input = jsonencode({
      source   = "eventbridge-scheduled-check"
      schedule = "daily-0205-utc"
      Records = [
        {
          s3 = {
            bucket = {
              name = var.input_bucket_name
            }
            object = {
              key = "patient_records_batch_001.csv"
            }
          }
        }
      ]
    })

    retry_policy {
      maximum_retry_attempts       = 3
      maximum_event_age_in_seconds = 3600
    }
  }
}
