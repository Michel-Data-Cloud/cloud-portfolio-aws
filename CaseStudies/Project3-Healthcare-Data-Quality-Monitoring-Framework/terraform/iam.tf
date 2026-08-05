# --- Lambda Execution Role ---
resource "aws_iam_role" "patient_data_quality_lambda_role" {
  name        = var.lambda_role_name
  description = "Execution role for Patient Data Quality Lambda functions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

# --- Managed Policy Attachments ---
# Note: These are the same broad managed policies used in the console
# build phase. Phase 2 Terraform will replace these with custom
# least-privilege inline policies scoped to specific resource ARNs.

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.patient_data_quality_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "s3_full_access" {
  role       = aws_iam_role.patient_data_quality_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "cloudwatch_full_access" {
  role       = aws_iam_role.patient_data_quality_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchFullAccess"
}

resource "aws_iam_role_policy_attachment" "sns_full_access" {
  role       = aws_iam_role.patient_data_quality_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSNSFullAccess"
}

