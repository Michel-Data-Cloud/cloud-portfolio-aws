# --- Bucket 1: Patient Data Input ---
resource "aws_s3_bucket" "patient_data_input" {
  bucket = var.input_bucket_name
}

resource "aws_s3_bucket_versioning" "patient_data_input_versioning" {
  bucket = aws_s3_bucket.patient_data_input.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "patient_data_input_block" {
  bucket                  = aws_s3_bucket.patient_data_input.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "patient_data_input_encryption" {
  bucket = aws_s3_bucket.patient_data_input.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# --- Bucket 2: Quality Results ---
resource "aws_s3_bucket" "patient_quality_results" {
  bucket = var.results_bucket_name
}

resource "aws_s3_bucket_versioning" "patient_quality_results_versioning" {
  bucket = aws_s3_bucket.patient_quality_results.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "patient_quality_results_block" {
  bucket                  = aws_s3_bucket.patient_quality_results.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "patient_quality_results_encryption" {
  bucket = aws_s3_bucket.patient_quality_results.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

