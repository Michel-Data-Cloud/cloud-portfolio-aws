variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "input_bucket_name" {
  description = "S3 bucket for raw patient data CSV exports from legacy EHR"
  type        = string
  default     = "project3-patient-data-input"
}

variable "results_bucket_name" {
  description = "S3 bucket for quality check results and reports"
  type        = string
  default     = "project3-patient-quality-results"
}

variable "lambda_role_name" {
  description = "IAM role name for Lambda execution"
  type        = string
  default     = "project3-patient-data-quality-lambda-role"
}

variable "freshness_hours" {
  description = "Maximum age in hours before a patient data file is flagged as stale"
  type        = number
  default     = 24
}

variable "alert_email" {
  description = "Email address to receive patient data quality alert notifications"
  type        = string
  default     = "foodtravelnature@gmail.com"
}
