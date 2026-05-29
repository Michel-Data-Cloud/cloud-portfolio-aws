"""
=============================================================================
Stream Aggregator Lambda Function
=============================================================================
Project      : Real-Time Streaming Analytics
Author       : [Your Name]
Phase        : 4 - Lambda Functions

Trigger      : Amazon EventBridge (scheduled, every 1 minute)
Purpose      : Queries DynamoDB for the last 5 minutes of sensor readings,
               computes windowed aggregations (avg/min/max temperature),
               publishes custom metrics to CloudWatch, and fires SNS anomaly
               alerts when average temperature exceeds the threshold.

Business Context:
    A single overheating sensor reading could be noise. But if the 5-minute
    average is above 90°C, that is a genuine problem — a machine is about
    to fail. This function implements that business logic.

Data Flow:
    EventBridge (1 min) → [THIS FUNCTION] → CloudWatch Custom Metrics
                                          → SNS Alert (if anomaly)

Well-Architected Notes:
    - Reliability   : Per-sensor try/except prevents one bad sensor from
                      blocking metrics for all other sensors.
    - Security      : SNS Topic ARN set via environment variable — no
                      hardcoded ARNs in source code.
    - Performance   : DynamoDB Query (not Scan) used for all data access.
                      Queries are O(result size), Scans are O(table size).
    - Cost          : CloudWatch PutMetricData batches up to 20 metrics per
                      API call — we publish individually for clarity here;
                      batching is a noted production enhancement.
=============================================================================
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# AWS Clients
# ---------------------------------------------------------------------------
dynamodb   = boto3.resource("dynamodb")
cloudwatch = boto3.client("cloudwatch")
sns        = boto3.client("sns")

# ---------------------------------------------------------------------------
# Configuration — use environment variables so nothing is hardcoded
# ---------------------------------------------------------------------------
TABLE_NAME      = os.environ.get("TABLE_NAME",      "project2-dynamo-table-streaming-analytics-sensor-readings")
SNS_TOPIC_ARN   = os.environ.get("SNS_TOPIC_ARN",   "PLACEHOLDER")   # Set after Phase 5
ANOMALY_THRESHOLD = float(os.environ.get("ANOMALY_THRESHOLD", "90"))
WINDOW_MINUTES    = int(os.environ.get("WINDOW_MINUTES",       "5"))
CW_NAMESPACE      = "StreamingAnalytics/Sensors"

table = dynamodb.Table(TABLE_NAME)

# ---------------------------------------------------------------------------
# Sensor registry — in production this would come from a config table or
# Parameter Store. Hardcoded here for simplicity in dev/learning.
# ---------------------------------------------------------------------------
SENSOR_IDS = [
    "sensor-floor-A-01",
    "sensor-floor-A-02",
    "sensor-floor-B-01",
    "sensor-floor-B-02",
]


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_time_window(minutes: int = WINDOW_MINUTES) -> tuple[str, str]:
    """
    Compute ISO 8601 timestamps for the start and end of the query window.

    Args:
        minutes: How many minutes back from now to query.

    Returns:
        Tuple of (start_time_iso, end_time_iso) strings.
    """
    end_time   = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=minutes)
    return start_time.isoformat(), end_time.isoformat()


def query_sensor_readings(sensor_id: str) -> list[dict]:
    """
    Query DynamoDB for all readings from a specific sensor in the time window.

    Uses the table's primary key (sensor_id + timestamp) for an efficient
    Query operation — NOT a Scan. This is critical for performance and cost.

    Args:
        sensor_id: The sensor's unique identifier string.

    Returns:
        List of DynamoDB item dictionaries for the sensor in the time window.
    """
    start_time, end_time = get_time_window(WINDOW_MINUTES)

    response = table.query(
        KeyConditionExpression=(
            Key("sensor_id").eq(sensor_id) &
            Key("timestamp").between(start_time, end_time)
        )
    )

    items = response.get("Items", [])
    logger.info(
        f"Queried DynamoDB | sensor_id={sensor_id} | "
        f"window={WINDOW_MINUTES}min | records_found={len(items)}"
    )
    return items


def compute_aggregations(items: list[dict]) -> dict | None:
    """
    Compute temperature statistics from a list of sensor reading records.

    Args:
        items: List of DynamoDB items returned from query_sensor_readings.

    Returns:
        Dictionary with avg, min, max, count — or None if no items.
    """
    if not items:
        return None

    temperatures = [float(item["temperature"]) for item in items]

    return {
        "avg":   round(sum(temperatures) / len(temperatures), 2),
        "min":   round(min(temperatures), 2),
        "max":   round(max(temperatures), 2),
        "count": len(temperatures),
    }


def publish_cloudwatch_metric(
    sensor_id:   str,
    metric_name: str,
    value:       float,
    unit:        str = "None"
) -> None:
    """
    Publish a single custom metric to CloudWatch under our namespace.

    Metrics appear in the CloudWatch dashboard we build in Phase 5.

    Args:
        sensor_id   : Used as a CloudWatch Dimension for per-sensor filtering.
        metric_name : Name of the metric (e.g. 'AvgTemperature').
        value       : Numeric value of the metric.
        unit        : CloudWatch unit string (e.g. 'Count', 'None').
    """
    cloudwatch.put_metric_data(
        Namespace=CW_NAMESPACE,
        MetricData=[{
            "MetricName": metric_name,
            "Dimensions": [
                {"Name": "SensorId", "Value": sensor_id}
            ],
            "Value":     value,
            "Unit":      unit,
            "Timestamp": datetime.now(timezone.utc),
        }]
    )
    logger.info(f"CloudWatch metric published | {metric_name}={value} | sensor={sensor_id}")


def send_anomaly_alert(sensor_id: str, aggregations: dict) -> None:
    """
    Publish an SNS notification when a sensor's average temperature
    exceeds the anomaly threshold.

    The SNS topic will fan-out to email subscribers (configured in Phase 5).

    Args:
        sensor_id    : The sensor that triggered the alert.
        aggregations : The computed stats dict from compute_aggregations.
    """
    if SNS_TOPIC_ARN == "PLACEHOLDER":
        logger.warning("SNS_TOPIC_ARN not set — skipping alert. Set this after Phase 5.")
        return

    alert_time = datetime.now(timezone.utc).isoformat()
    message = (
        f"ANOMALY ALERT — Manufacturing Floor Sensor\n"
        f"{'=' * 50}\n"
        f"Sensor ID  : {sensor_id}\n"
        f"Avg Temp   : {aggregations['avg']}°C  (threshold: {ANOMALY_THRESHOLD}°C)\n"
        f"Max Temp   : {aggregations['max']}°C\n"
        f"Min Temp   : {aggregations['min']}°C\n"
        f"Readings   : {aggregations['count']} in last {WINDOW_MINUTES} minutes\n"
        f"Alert Time : {alert_time}\n"
        f"{'=' * 50}\n"
        f"ACTION REQUIRED: Inspect sensor location immediately.\n"
        f"Sustained temperatures above {ANOMALY_THRESHOLD}°C risk equipment damage."
    )

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"[ALERT] Sensor {sensor_id} overheating — avg {aggregations['avg']}°C",
        Message=message,
    )
    logger.warning(
        f"Anomaly alert sent | sensor_id={sensor_id} | avg_temp={aggregations['avg']}"
    )


# ---------------------------------------------------------------------------
# Lambda Handler — Entry Point
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context) -> dict:
    """
    Main Lambda entry point. Runs on a 1-minute EventBridge schedule.

    For each known sensor:
        1. Query DynamoDB for the last 5 minutes of readings
        2. Compute aggregations (avg/min/max temperature)
        3. Publish metrics to CloudWatch
        4. Send SNS alert if avg temperature exceeds threshold

    Args:
        event   : EventBridge scheduled event (contents not used).
        context : Lambda runtime context.

    Returns:
        Dictionary summarising how many sensors were processed.
    """
    run_time = datetime.now(timezone.utc).isoformat()
    logger.info(f"Aggregator invoked | time={run_time} | sensors={len(SENSOR_IDS)}")

    processed = 0
    skipped   = 0
    errors    = 0

    for sensor_id in SENSOR_IDS:
        try:
            # Step 1: Query DynamoDB
            items = query_sensor_readings(sensor_id)

            if not items:
                logger.info(f"No data in window for {sensor_id} — skipping")
                skipped += 1
                continue

            # Step 2: Compute stats
            agg = compute_aggregations(items)

            logger.info(
                f"Aggregation complete | sensor={sensor_id} | "
                f"avg={agg['avg']} | min={agg['min']} | "
                f"max={agg['max']} | count={agg['count']}"
            )

            # Step 3: Publish to CloudWatch
            publish_cloudwatch_metric(sensor_id, "AvgTemperature", agg["avg"])
            publish_cloudwatch_metric(sensor_id, "MaxTemperature", agg["max"])
            publish_cloudwatch_metric(sensor_id, "MinTemperature", agg["min"])
            publish_cloudwatch_metric(sensor_id, "RecordCount",    agg["count"], unit="Count")

            # Step 4: Anomaly detection
            if agg["avg"] >= ANOMALY_THRESHOLD:
                send_anomaly_alert(sensor_id, agg)

            processed += 1

        except ClientError as e:
            errors += 1
            logger.error(
                f"AWS error for {sensor_id}: "
                f"{e.response['Error']['Code']}: {e.response['Error']['Message']}"
            )

        except Exception as e:
            errors += 1
            logger.error(f"Unexpected error for {sensor_id}: {str(e)}")

    logger.info(
        f"Aggregator complete | processed={processed} | "
        f"skipped={skipped} | errors={errors}"
    )

    return {
        "statusCode": 200,
        "processed":  processed,
        "skipped":    skipped,
        "errors":     errors,
    }
