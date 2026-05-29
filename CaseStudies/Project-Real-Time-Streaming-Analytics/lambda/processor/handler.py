"""
=============================================================================
Stream Processor Lambda Function
=============================================================================
Project      : Real-Time Streaming Analytics
Author       : [Your Name]
Phase        : 4 - Lambda Functions

Trigger      : Amazon Kinesis Data Stream (streaming-analytics-sensor-stream)
Purpose      : Reads batches of IoT sensor records from Kinesis, decodes and
               validates each record, enriches it with a status field and TTL,
               then writes it to DynamoDB.

Business Context:
    Manufacturing plant IoT sensors emit temperature, pressure, and humidity
    readings every second. This function is the first processing layer —
    it turns raw stream events into structured, queryable DynamoDB items.

Data Flow:
    Kinesis Stream → [THIS FUNCTION] → DynamoDB Table

Well-Architected Notes:
    - Reliability   : Per-record try/except ensures one bad record doesn't
                      fail the entire batch (partial batch failure handling).
    - Security      : No hardcoded credentials. IAM role provides all access.
    - Performance   : Batch writes processed sequentially; can be upgraded
                      to batch_writer() for higher throughput in production.
    - Cost          : Lambda billed per 100ms. Minimal memory (256MB) keeps
                      cost low for this workload.
=============================================================================
"""

import json
import base64
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Logging — CloudWatch Logs automatically captures this output
# ---------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# AWS Clients — instantiated outside handler for Lambda container reuse
# (warm starts reuse the same container, so this saves init time)
# ---------------------------------------------------------------------------
dynamodb = boto3.resource("dynamodb")
TABLE_NAME = "project2-dynamo-table-streaming-analytics-sensor-readings"
table = dynamodb.Table(TABLE_NAME)

# ---------------------------------------------------------------------------
# Business Logic Constants
# ---------------------------------------------------------------------------
ANOMALY_THRESHOLD_CRITICAL = 90   # °C — immediate action required
ANOMALY_THRESHOLD_WARNING  = 80   # °C — monitor closely
TTL_DAYS = 7                      # Auto-delete records after 7 days (cost control)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def determine_status(temperature: float) -> str:
    """
    Derive a human-readable status from the raw temperature value.
    This enrichment makes downstream querying and alerting simpler.

    Args:
        temperature: Sensor temperature reading in degrees Celsius.

    Returns:
        'critical' | 'warning' | 'normal'
    """
    if temperature >= ANOMALY_THRESHOLD_CRITICAL:
        return "critical"
    elif temperature >= ANOMALY_THRESHOLD_WARNING:
        return "warning"
    return "normal"


def compute_ttl(days: int = TTL_DAYS) -> int:
    """
    Compute the Unix epoch timestamp N days from now.
    DynamoDB TTL uses this to automatically delete expired items at no charge.

    Args:
        days: Number of days until the record expires.

    Returns:
        Integer Unix timestamp.
    """
    return int(time.time()) + (days * 86400)


def decode_kinesis_record(record: dict) -> dict:
    """
    Decode a base64-encoded Kinesis record payload into a Python dict.

    Kinesis stores data as base64 strings. This function decodes and
    deserializes the JSON payload back into a usable Python dictionary.

    Args:
        record: A single record from event['Records'].

    Returns:
        Decoded Python dictionary of sensor data.

    Raises:
        ValueError: If the payload is not valid JSON.
    """
    raw_data = record["kinesis"]["data"]
    decoded_bytes = base64.b64decode(raw_data)
    decoded_str = decoded_bytes.decode("utf-8")
    return json.loads(decoded_str)


def enrich_record(sensor_data: dict) -> dict:
    """
    Add derived fields to the raw sensor record before writing to DynamoDB.

    Fields added:
        - status       : 'normal' | 'warning' | 'critical' based on temperature
        - ttl          : Unix epoch for DynamoDB auto-deletion
        - processed_at : ISO timestamp of when this Lambda processed the record

    Args:
        sensor_data: Decoded sensor payload from Kinesis.

    Returns:
        Enriched sensor data dictionary.
    """
    temperature = float(sensor_data["temperature"])
    sensor_data["status"]       = determine_status(temperature)
    sensor_data["ttl"]          = compute_ttl(days=TTL_DAYS)
    sensor_data["processed_at"] = datetime.now(timezone.utc).isoformat()
    return sensor_data


def convert_floats_to_decimal(data: dict) -> dict:
    """
    DynamoDB does not accept Python float types — it requires Decimal.
    This function recursively converts all float values in a dict.

    Args:
        data: Dictionary potentially containing float values.

    Returns:
        Dictionary with all floats replaced by Decimal equivalents.
    """
    return {
        k: Decimal(str(v)) if isinstance(v, float) else v
        for k, v in data.items()
    }


def write_to_dynamodb(item: dict) -> None:
    """
    Write a single enriched sensor record to DynamoDB.

    Args:
        item: Fully enriched and Decimal-converted sensor record.

    Raises:
        ClientError: If the DynamoDB put_item call fails.
    """
    table.put_item(Item=item)


# ---------------------------------------------------------------------------
# Lambda Handler — Entry Point
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context) -> dict:
    """
    Main Lambda entry point. Processes a batch of Kinesis records.

    Kinesis triggers Lambda with batches of records (up to 100 in our config).
    Each record is processed independently — a failure on one record is logged
    but does not stop processing of the remaining records in the batch.

    Args:
        event   : Kinesis trigger event containing a list of records.
        context : Lambda runtime context (used for logging function name etc).

    Returns:
        Dictionary with HTTP-style status code and success/failure counts.
    """
    total_records = len(event["Records"])
    logger.info(
        f"Processor invoked | function={context.function_name} "
        f"| batch_size={total_records}"
    )

    success_count = 0
    failure_count = 0

    for i, record in enumerate(event["Records"]):
        try:
            # Step 1: Decode the base64 Kinesis payload
            sensor_data = decode_kinesis_record(record)

            # Step 2: Enrich with derived fields (status, TTL, processed_at)
            sensor_data = enrich_record(sensor_data)

            # Step 3: Convert floats → Decimal (DynamoDB requirement)
            item = convert_floats_to_decimal(sensor_data)

            # Step 4: Write to DynamoDB
            write_to_dynamodb(item)

            success_count += 1
            logger.info(
                f"Record {i+1}/{total_records} written | "
                f"sensor_id={sensor_data.get('sensor_id')} | "
                f"timestamp={sensor_data.get('timestamp')} | "
                f"temperature={sensor_data.get('temperature')} | "
                f"status={sensor_data.get('status')}"
            )

        except (KeyError, ValueError, json.JSONDecodeError) as e:
            # Bad data format — log and skip, don't retry
            failure_count += 1
            logger.error(
                f"Record {i+1}/{total_records} SKIPPED — bad format: {str(e)}"
            )

        except ClientError as e:
            # DynamoDB write failure — log and continue
            failure_count += 1
            logger.error(
                f"Record {i+1}/{total_records} FAILED — DynamoDB error: "
                f"{e.response['Error']['Code']}: {e.response['Error']['Message']}"
            )

        except Exception as e:
            # Catch-all for unexpected errors
            failure_count += 1
            logger.error(
                f"Record {i+1}/{total_records} FAILED — unexpected error: {str(e)}"
            )

    # Summary log — visible in CloudWatch Logs for monitoring
    logger.info(
        f"Batch complete | total={total_records} | "
        f"success={success_count} | failed={failure_count}"
    )

    return {
        "statusCode": 200,
        "total":   total_records,
        "success": success_count,
        "failed":  failure_count,
    }
