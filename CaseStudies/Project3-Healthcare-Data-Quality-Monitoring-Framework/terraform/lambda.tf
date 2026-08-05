# --- Lambda Function Archive ---
# Packages the Python source file into a zip for deployment.
# The source file lives in the lambda/ directory at project root.
data "archive_file" "quality_engine" {
  type        = "zip"
  source_file = "${path.module}/../lambda/lambda_function.py"
  output_path = "${path.module}/../lambda/lambda_function.zip"
}

# --- Patient Data Quality Engine Lambda ---
resource "aws_lambda_function" "quality_engine" {
  function_name    = "project3-patient-data-quality-engine"
  description      = "Validates patient records migrated from legacy EHR system. Detects missing fields, schema violations, duplicate MRNs, out-of-range vitals, business rule violations, and stale data."
  role             = aws_iam_role.patient_data_quality_lambda_role.arn
  runtime          = "python3.11"
  handler          = "lambda_function.lambda_handler"
  filename         = data.archive_file.quality_engine.output_path
  source_code_hash = data.archive_file.quality_engine.output_base64sha256
  timeout          = 60
  memory_size      = 128

  environment {
    variables = {
      RESULTS_BUCKET  = var.results_bucket_name
      FRESHNESS_HOURS = "24"
    }
  }
}

# --- CloudWatch Log Group for Lambda ---
# Explicit log group gives us control over retention period.
# Without this, Lambda auto-creates a log group with infinite retention.
resource "aws_cloudwatch_log_group" "quality_engine_logs" {
  name              = "/aws/lambda/patient-data-quality-engine"
  retention_in_days = 30
}

# --- S3 Event Trigger ---
# Grants S3 permission to invoke the Lambda function.
# The trigger fires only on PUT events for .csv files —
# deliberately chosen to avoid unintended invocations
# from copy or multipart upload operations.
resource "aws_lambda_permission" "allow_s3_trigger" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.quality_engine.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.patient_data_input.arn
}

resource "aws_s3_bucket_notification" "patient_data_trigger" {
  bucket = aws_s3_bucket.patient_data_input.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.quality_engine.arn
    events              = ["s3:ObjectCreated:Put"]
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.allow_s3_trigger]
}
