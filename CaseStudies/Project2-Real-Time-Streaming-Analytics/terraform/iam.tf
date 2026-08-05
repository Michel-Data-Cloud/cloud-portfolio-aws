# =============================================================================
# IAM ROLES & POLICIES — LEAST PRIVILEGE PER LAMBDA FUNCTION
# =============================================================================
# Purpose : Define the security identities for both Lambda functions.
#           Each function gets its own role scoped to exactly the resources
#           and actions it needs — nothing more.
#
# Design Decisions:
#   - Two separate roles (processor + aggregator) rather than one shared role.
#     A shared role would over-permission both functions. Least privilege
#     requires per-function roles.
#
#   - Custom inline policies scoped to specific resource ARNs rather than
#     AWS managed policies (e.g. AmazonDynamoDBFullAccess).
#     This is a SECURITY IMPROVEMENT over the console build where managed
#     policies were used for speed during learning. In production (and in
#     this IaC), we scope every permission to the exact resource it needs.
#
#   - CloudWatch Logs permissions are explicit rather than relying on
#     AWSLambdaBasicExecutionRole. This makes the permission surface visible
#     and auditable in code review.
#
# Well-Architected:
#   - Security : Least privilege, no wildcard resources on sensitive actions,
#                all permissions traceable to a specific business need.
# =============================================================================


# -----------------------------------------------------------------------------
# SHARED: Lambda Trust Policy
# Both Lambda roles share the same trust policy — allows the Lambda
# service to assume the role when a function is invoked.
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "lambda_trust_policy" {
  statement {
    sid     = "AllowLambdaAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}


# =============================================================================
# PROCESSOR LAMBDA ROLE
# Permissions needed:
#   1. Write logs to CloudWatch Logs
#   2. Read records from the Kinesis stream
#   3. Write items to the DynamoDB sensor readings table
# =============================================================================

resource "aws_iam_role" "processor_role" {
  name               = "${var.project_name}-processor-role"
  description        = "Execution role for the Kinesis stream processor Lambda. Scoped to Kinesis read + DynamoDB write on specific resources."
  assume_role_policy = data.aws_iam_policy_document.lambda_trust_policy.json

  tags = {
    Name = "${var.project_name}-processor-role"
  }
}

# Custom policy for the processor role
data "aws_iam_policy_document" "processor_policy_doc" {

  # --- Permission 1: CloudWatch Logs ---
  # Required for Lambda to write execution logs.
  # Scoped to the specific log group for this function.
  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-stream-processor",
      "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-stream-processor:*",
    ]
  }

  # --- Permission 2: Kinesis Stream Read ---
  # Required for the Lambda Kinesis trigger to poll and read records.
  # Scoped to our specific stream ARN.
  statement {
    sid    = "AllowKinesisRead"
    effect = "Allow"
    actions = [
      "kinesis:GetRecords",
      "kinesis:GetShardIterator",
      "kinesis:DescribeStream",
      "kinesis:DescribeStreamSummary",
      "kinesis:ListShards",
      "kinesis:ListStreams",
    ]
    resources = [aws_kinesis_stream.sensor_stream.arn]
  }

  # --- Permission 3: DynamoDB Write ---
  # Required to write enriched sensor records to the table.
  # Scoped to our specific table ARN only — not all DynamoDB tables.
  statement {
    sid    = "AllowDynamoDBWrite"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:DescribeTable",
    ]
    resources = [aws_dynamodb_table.sensor_readings.arn]
  }
}

resource "aws_iam_policy" "processor_policy" {
  name        = "${var.project_name}-processor-policy"
  description = "Least-privilege policy for the stream processor Lambda. Grants Kinesis read, DynamoDB write, and CloudWatch Logs on specific resources."
  policy      = data.aws_iam_policy_document.processor_policy_doc.json

  tags = {
    Name = "${var.project_name}-processor-policy"
  }
}

resource "aws_iam_role_policy_attachment" "processor_policy_attachment" {
  role       = aws_iam_role.processor_role.name
  policy_arn = aws_iam_policy.processor_policy.arn
}


# =============================================================================
# AGGREGATOR LAMBDA ROLE
# Permissions needed:
#   1. Write logs to CloudWatch Logs
#   2. Read items from the DynamoDB sensor readings table
#   3. Publish custom metrics to CloudWatch
#   4. Publish anomaly alert messages to the SNS topic
# =============================================================================

resource "aws_iam_role" "aggregator_role" {
  name               = "${var.project_name}-aggregator-role"
  description        = "Execution role for the aggregator Lambda. Scoped to DynamoDB read + CloudWatch metrics + SNS publish on specific resources."
  assume_role_policy = data.aws_iam_policy_document.lambda_trust_policy.json

  tags = {
    Name = "${var.project_name}-aggregator-role"
  }
}

# Custom policy for the aggregator role
data "aws_iam_policy_document" "aggregator_policy_doc" {

  # --- Permission 1: CloudWatch Logs ---
  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-stream-aggregator",
      "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-stream-aggregator:*",
    ]
  }

  # --- Permission 2: DynamoDB Read ---
  # Required to query sensor readings for aggregation.
  # Read-only — the aggregator never writes to the table.
  # Scoped to our specific table and its GSI.
  statement {
    sid    = "AllowDynamoDBRead"
    effect = "Allow"
    actions = [
      "dynamodb:Query",
      "dynamodb:GetItem",
      "dynamodb:DescribeTable",
    ]
    resources = [
      aws_dynamodb_table.sensor_readings.arn,
      "${aws_dynamodb_table.sensor_readings.arn}/index/*",
    ]
  }

  # --- Permission 3: CloudWatch Custom Metrics ---
  # Required to publish AvgTemperature, MaxTemperature, etc.
  # Scoped to our custom namespace only.
  statement {
    sid    = "AllowCloudWatchMetrics"
    effect = "Allow"
    actions = [
      "cloudwatch:PutMetricData",
    ]
    # CloudWatch PutMetricData does not support resource-level restrictions.
    # The namespace condition below narrows the scope as much as AWS allows.
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["StreamingAnalytics/Sensors"]
    }
  }

  # --- Permission 4: SNS Publish ---
  # Required to send anomaly alert notifications.
  # Scoped to our specific SNS topic ARN only.
  statement {
    sid    = "AllowSNSPublish"
    effect = "Allow"
    actions = [
      "sns:Publish",
    ]
    resources = [aws_sns_topic.anomaly_alerts.arn]
  }
}

resource "aws_iam_policy" "aggregator_policy" {
  name        = "${var.project_name}-aggregator-policy"
  description = "Least-privilege policy for the aggregator Lambda. Grants DynamoDB read, CloudWatch metrics, SNS publish on specific resources."
  policy      = data.aws_iam_policy_document.aggregator_policy_doc.json

  tags = {
    Name = "${var.project_name}-aggregator-policy"
  }
}

resource "aws_iam_role_policy_attachment" "aggregator_policy_attachment" {
  role       = aws_iam_role.aggregator_role.name
  policy_arn = aws_iam_policy.aggregator_policy.arn
}
