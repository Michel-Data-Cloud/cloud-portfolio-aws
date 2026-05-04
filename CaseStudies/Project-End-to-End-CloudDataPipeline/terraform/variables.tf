################################################################################
# VARIABLES FOR PROJECT1 DECEMBER 2025 BASELINE
################################################################################

variable "aws_region" {
  description = "AWS region where resources are deployed"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID (used for bucket naming)"
  type        = string
  default     = "022779559958"
}

variable "project_name" {
  description = "Project name used for tagging"
  type        = string
  default     = "Project1-DataPipeline"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "Production"
}

variable "baseline_date" {
  description = "Baseline creation date for documentation"
  type        = string
  default     = "December2025"
}
