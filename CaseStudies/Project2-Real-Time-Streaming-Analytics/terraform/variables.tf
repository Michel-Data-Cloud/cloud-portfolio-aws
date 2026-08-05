# =============================================================================
# GLOBAL VARIABLES
# These are reused across all Terraform files in this project.
# =============================================================================

variable "aws_region" {
  description = "AWS region to deploy all resources into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short name for this project, used as a prefix on all resource names"
  type        = string
  default     = "streaming-analytics"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

# =============================================================================
# KINESIS VARIABLES
# =============================================================================

variable "kinesis_shard_count" {
  description = <<-EOT
    Number of shards for the Kinesis Data Stream.
    Each shard supports:
      - Ingest:  1 MB/s  or 1,000 records/s
      - Egress:  2 MB/s
    Start with 1 for dev/learning; scale up for production workloads.
  EOT
  type        = number
  default     = 1
}

variable "kinesis_retention_hours" {
  description = "How long (in hours) Kinesis retains stream records. Min: 24, Max: 8760 (365 days)"
  type        = number
  default     = 24
}

# =============================================================================
# DYNAMODB VARIABLES
# =============================================================================

variable "dynamodb_billing_mode" {
  description = <<-EOT
    DynamoDB billing mode:
      - PAY_PER_REQUEST: Serverless, scales automatically — best for unpredictable workloads
      - PROVISIONED:     Fixed RCU/WCU capacity — best for predictable workloads
    We use PAY_PER_REQUEST for this project to avoid surprise costs while learning.
  EOT
  type        = string
  default     = "PAY_PER_REQUEST"
}

# =============================================================================
# LAMBDA VARIABLES
# =============================================================================

variable "lambda_runtime" {
  description = "Python runtime version for all Lambda functions in this project"
  type        = string
  default     = "python3.11"
}

variable "lambda_timeout_seconds" {
  description = "Max execution time (seconds) for Lambda functions. Kinesis processor max recommended: 300"
  type        = number
  default     = 60
}

variable "lambda_memory_mb" {
  description = "Memory allocated to each Lambda function in MB. More memory = more CPU too."
  type        = number
  default     = 256
}

variable "processor_batch_size" {
  description = <<-EOT
    Number of Kinesis records Lambda pulls per batch.
    Higher = more efficient, but longer processing time per invocation.
    Range: 1–10,000. Use 100 for learning/dev.
  EOT
  type        = number
  default     = 100
}

# =============================================================================
# SNS / ALERTING VARIABLES
# =============================================================================

variable "alert_email" {
  description = "Email address that will receive SNS anomaly alert notifications"
  type        = string
  default     = ""  # <-- Empty default. Value comes from terraform.tfvars
}

# =============================================================================
# CLOUDWATCH VARIABLES
# =============================================================================

variable "anomaly_threshold" {
  description = "Sensor value above this number triggers an SNS anomaly alert"
  type        = number
  default     = 90
}
