# =============================================================================
# DYNAMODB TABLE — sensor_readings
# =============================================================================
# Purpose : Persistent NoSQL storage for all IoT sensor readings.
#           Designed around the access patterns of the pipeline, not a
#           relational schema.
#
# Key Design (access-pattern-first):
#   Partition Key : sensor_id  (String)
#     → Distributes data evenly across partitions.
#     → Enables efficient per-sensor queries.
#     → Avoids hot partitions (all sensors write simultaneously, but to
#       different partition keys).
#
#   Sort Key      : timestamp  (String, ISO 8601)
#     → Enables time-range queries: "give me all readings for sensor X
#       between time Y and time Z."
#     → Naturally ordered — DynamoDB sorts lexicographically, and ISO 8601
#       timestamps sort correctly as strings.
#
# Access Patterns Supported:
#   1. Write one sensor reading           → PutItem (processor Lambda)
#   2. Read all readings for sensor in    → Query on PK + SK range
#      last 5 minutes                       (aggregator Lambda)
#   3. Read all sensors at a location     → Query on GSI (ops team)
#
# Global Secondary Index (location-timestamp-index):
#   → Enables access pattern 3 without a full table scan.
#   → Partition key: location, Sort key: timestamp
#   → Example query: "all sensors on floor-A in last 10 minutes"
#
# TTL (Time to Live):
#   → Attribute: ttl (Unix epoch integer)
#   → Records auto-delete 7 days after creation at no charge.
#   → Prevents unbounded storage growth from continuous IoT ingest.
#   → Long-term archival handled by Kinesis Data Firehose → S3 (enhancement).
#
# Well-Architected:
#   - Reliability  : DynamoDB is multi-AZ by default. On-demand scales
#                    automatically — no throttling during burst writes.
#   - Security     : Encryption at rest via DynamoDB owned key (free).
#                    Production: Customer Managed Key (CMK) via KMS.
#   - Cost         : On-demand for dev (no idle capacity cost). Switch to
#                    Provisioned at sustained load for ~30% savings.
#   - Performance  : All queries use KeyConditionExpression (never Scan).
#                    GSI enables location queries without full table scan.
# =============================================================================

resource "aws_dynamodb_table" "sensor_readings" {
  name         = "${var.project_name}-sensor-readings"
  billing_mode = var.dynamodb_billing_mode

  # -------------------------------------------------------------------------
  # Primary Key Definition
  # -------------------------------------------------------------------------
  hash_key  = "sensor_id"   # Partition key
  range_key = "timestamp"   # Sort key

  attribute {
    name = "sensor_id"
    type = "S"   # String
  }

  attribute {
    name = "timestamp"
    type = "S"   # String (ISO 8601 — sorts lexicographically)
  }

  # -------------------------------------------------------------------------
  # GSI attribute — must be declared here even though it is only used
  # in the global_secondary_index block below
  # -------------------------------------------------------------------------
  attribute {
    name = "location"
    type = "S"
  }

  # -------------------------------------------------------------------------
  # Global Secondary Index: location-timestamp-index
  # Enables ops team queries: "all sensors at floor-A in last 10 minutes"
  # Without this GSI, that query requires a full table scan.
  # -------------------------------------------------------------------------
  global_secondary_index {
    name            = "location-timestamp-index"
    hash_key        = "location"
    range_key       = "timestamp"
    projection_type = "ALL"   # Project all attributes to the index
    # Note: For PAY_PER_REQUEST billing mode, read/write capacity is
    # managed automatically — no read_capacity/write_capacity needed.
  }

  # -------------------------------------------------------------------------
  # TTL Configuration
  # DynamoDB reads the 'ttl' attribute on each item and automatically
  # deletes items whose ttl value is in the past. Deletion is free,
  # asynchronous, and typically occurs within 48 hours of expiry.
  # -------------------------------------------------------------------------
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # -------------------------------------------------------------------------
  # Encryption at Rest
  # DynamoDB owned key = free, automatic, transparent.
  # Production enhancement: set enabled=true and specify a KMS key ARN
  # for a Customer Managed Key with full rotation and audit trail.
  # DynamoDB encrypts at rest by default using a DynamoDB owned key. 
  # This block is optional --> "enabled = false"
  # -------------------------------------------------------------------------
  server_side_encryption {
    enabled = false   # false = DynamoDB owned key (still encrypted, just not CMK)
  }

  # Point-in-time recovery (PITR)
  # Allows restore to any second in the last 35 days.
  # Disabled for dev (cost: ~$0.20/GB/month).
  # Production: always enable PITR.
  point_in_time_recovery {
    enabled = false
  }

  tags = {
    Name = "${var.project_name}-sensor-readings"
  }
}
