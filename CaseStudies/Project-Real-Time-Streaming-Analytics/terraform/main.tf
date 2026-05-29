terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # -----------------------------------------------------------------------------
  # OPTIONAL: Remote state backend (recommended for real projects)
  # Uncomment and replace bucket/region after you manually create an S3 bucket
  # for Terraform state storage.
  # -----------------------------------------------------------------------------
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket-name"
  #   key    = "streaming-analytics/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# -----------------------------------------------------------------------------
# Data sources — these reference existing AWS account info at plan/apply time
# -----------------------------------------------------------------------------

# Retrieves the current AWS account ID, used in IAM policies
data "aws_caller_identity" "current" {}

# Retrieves the current AWS region
data "aws_region" "current" {}
