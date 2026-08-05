# =============================================================================
# KINESIS DATA STREAM
# =============================================================================
# Purpose : Real-time ingestion highway for IoT sensor data.
#           Every sensor reading flows through this stream before being
#           processed by the stream processor Lambda function.
#
# Design Decisions:
#   - Provisioned mode (1 shard) chosen deliberately for learning/portfolio.
#     Each shard supports 1MB/s ingest and 2MB/s egress.
#     Production recommendation: On-demand mode for unpredictable IoT load.
#
#   - 24-hour retention is the minimum (and free tier limit).
#     Extended retention (up to 365 days) costs $0.023/shard/hour.
#     For this workload, 24 hours is sufficient — failed records are
#     replayed from the DLQ, not the stream.
#
#   - Encryption at rest using the AWS managed KMS key for Kinesis.
#     Production enhancement: Customer Managed Key (CMK) for full
#     key control and CloudTrail audit trail.
#
# Well-Architected:
#   - Reliability    : Kinesis replicates data across 3 AZs by default.
#   - Security       : Encryption at rest enabled.
#   - Cost           : $0.015/shard/hour. Delete when not testing.
#   - Performance    : 1 shard = 1,000 records/s or 1MB/s — sufficient
#                      for 4 sensors at 1 record/second each.
# =============================================================================

resource "aws_kinesis_stream" "sensor_stream" {
  name             = "${var.project_name}-sensor-stream"
  shard_count      = var.kinesis_shard_count
  retention_period = var.kinesis_retention_hours

  # Encryption at rest using AWS managed KMS key
  # Production: switch to a Customer Managed Key (CMK) for full audit trail
  encryption_type = "KMS"
  kms_key_id      = "alias/aws/kinesis"

  # Stream-level tags (merged with provider default_tags)
  tags = {
    Name = "${var.project_name}-sensor-stream"
  }
}
