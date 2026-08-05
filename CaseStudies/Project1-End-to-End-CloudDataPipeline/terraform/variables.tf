################################################################################
# PROJECT 1 — END-TO-END AWS DATA PIPELINE
# Terraform Variable Definitions
################################################################################

variable "aws_region" {
  description = "AWS region where all pipeline resources are deployed"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID, used in S3 bucket naming for Glue assets"
  type        = string
  default     = "022779559958"
}

variable "project_name" {
  description = "Project name used for resource tagging and identification"
  type        = string
  default     = "Project1-DataPipeline"
}

variable "environment" {
  description = "Deployment environment (Production / Staging / Development)"
  type        = string
  default     = "Production"

  validation {
    condition     = contains(["Production", "Staging", "Development"], var.environment)
    error_message = "environment must be one of: Production, Staging, Development."
  }
}

variable "baseline_date" {
  description = "Baseline creation date for documentation and change tracking"
  type        = string
  default     = "June2026"
}

variable "alert_email" {
  description = "Email address to receive pipeline failure alerts via SNS. Override in terraform.tfvars (gitignored) before applying."
  type        = string
  default     = ""

  validation {
    condition     = length(var.alert_email) > 0
    error_message = "alert_email must be set. Add 'alert_email = \"your-email@example.com\"' to terraform.tfvars."
  }
}
