"""
=============================================================================
IoT Sensor Data Producer
=============================================================================
Project      : Real-Time Streaming Analytics
Author       : [Your Name]
Phase        : 6 - End-to-End Test
 
Purpose:
    Simulates a manufacturing plant's IoT sensor network by generating
    realistic sensor readings and publishing them to a Kinesis Data Stream
    in real time.
 
    This script acts as the DATA SOURCE for the entire pipeline:
 
        [THIS SCRIPT] → Kinesis → Lambda Processor → DynamoDB
                                                         ↓
                               SNS Alert ← Lambda Aggregator → CloudWatch
 
Business Context:
    In production, physical IoT sensors would publish directly to Kinesis
    via the AWS IoT Core service or Kinesis Agent. This script replicates
    that behavior for local development and portfolio demonstration.
 
Modes:
    normal  — Temperatures fluctuate realistically between 60–85°C
    anomaly — One sensor spikes above 90°C to trigger the SNS alert
 
Usage:
    # Normal mode (default) — runs indefinitely, Ctrl+C to stop
    python producer.py
 
    # Anomaly mode — spikes sensor-floor-A-01 above threshold
    python producer.py --mode anomaly
 
    # Custom duration — run for 60 seconds then stop
    python producer.py --duration 60
 
    # Custom interval — send every 2 seconds instead of 1
    python producer.py --interval 2
 
Well-Architected Notes:
    - Reliability  : Exponential backoff on Kinesis PutRecord failures.
    - Observability: Structured console output matches Lambda log format
                     so behavior is easy to trace end-to-end.
    - Cost         : Default 1-second interval generates ~3,600 records/hour
                     per sensor — well within 1-shard Kinesis capacity and
                     DynamoDB free tier for a dev session.
=============================================================================
"""
 
import argparse
import json
import logging
import random
import sys
import time
from datetime import datetime, timezone
 
import boto3
from botocore.exceptions import ClientError
 
# ---------------------------------------------------------------------------
# Logging — structured output matches Lambda log style
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)
 
# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
STREAM_NAME = "project2-streaming-analytics-sensor-stream"
REGION      = "us-east-1"
 
# Sensor registry — must match SENSOR_IDS in aggregator Lambda
SENSORS = [
    {"sensor_id": "sensor-floor-A-01", "location": "floor-A"},
    {"sensor_id": "sensor-floor-A-02", "location": "floor-A"},
    {"sensor_id": "sensor-floor-B-01", "location": "floor-B"},
    {"sensor_id": "sensor-floor-B-02", "location": "floor-B"},
]
 
# Normal operating ranges for each sensor reading type
NORMAL_RANGES = {
    "temperature": (60.0, 85.0),   # °C — healthy operating range
    "pressure":    (980.0, 1040.0), # hPa — atmospheric pressure range
    "humidity":    (30.0, 65.0),    # %RH — relative humidity range
}
 
# Anomaly simulation — spike one sensor above the 90°C threshold
ANOMALY_SENSOR_ID = "sensor-floor-A-01"
ANOMALY_TEMP_RANGE = (91.0, 98.0)  # °C — clearly above 90°C threshold
 
# Retry configuration for Kinesis PutRecord
MAX_RETRIES    = 3
BASE_DELAY_SEC = 0.5  # doubles on each retry (exponential backoff)
 
 
# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
 
def generate_sensor_reading(sensor: dict, anomaly_mode: bool) -> dict:
    """
    Generate a single realistic sensor reading for one IoT device.
 
    In normal mode, all values fall within healthy operating ranges.
    In anomaly mode, the designated anomaly sensor emits temperatures
    above the 90°C alert threshold.
 
    Args:
        sensor      : Dict with sensor_id and location keys.
        anomaly_mode: If True, spike the anomaly sensor temperature.
 
    Returns:
        Dictionary representing one sensor reading event.
    """
    is_anomaly_sensor = (
        anomaly_mode and sensor["sensor_id"] == ANOMALY_SENSOR_ID
    )
 
    if is_anomaly_sensor:
        temperature = round(random.uniform(*ANOMALY_TEMP_RANGE), 2)
    else:
        temperature = round(random.uniform(*NORMAL_RANGES["temperature"]), 2)
 
    return {
        "sensor_id":   sensor["sensor_id"],
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "temperature": temperature,
        "pressure":    round(random.uniform(*NORMAL_RANGES["pressure"]), 2),
        "humidity":    round(random.uniform(*NORMAL_RANGES["humidity"]), 2),
        "location":    sensor["location"],
    }
 
 
def put_record_with_retry(
    client,
    stream_name: str,
    data: dict,
    partition_key: str,
) -> bool:
    """
    Publish one record to Kinesis with exponential backoff retry logic.
 
    Kinesis can occasionally return ProvisionedThroughputExceededException
    for a shard — retrying with backoff handles this gracefully without
    data loss.
 
    Args:
        client        : Boto3 Kinesis client.
        stream_name   : Name of the target Kinesis stream.
        data          : Python dict to serialize and publish.
        partition_key : Kinesis partition key — determines which shard
                        receives this record. We use sensor_id so all
                        readings from one sensor go to the same shard
                        (preserves ordering per sensor).
 
    Returns:
        True if record was published successfully, False after all retries.
    """
    payload = json.dumps(data)
    delay   = BASE_DELAY_SEC
 
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.put_record(
                StreamName=stream_name,
                Data=payload.encode("utf-8"),
                PartitionKey=partition_key,
            )
            shard_id        = response["ShardId"]
            sequence_number = response["SequenceNumber"]
            logger.debug(
                f"Published | sensor={partition_key} | "
                f"shard={shard_id} | seq={sequence_number[-6:]}"
            )
            return True
 
        except client.exceptions.ProvisionedThroughputExceededException:
            logger.warning(
                f"Throughput exceeded (attempt {attempt}/{MAX_RETRIES}) "
                f"for {partition_key} — retrying in {delay}s"
            )
            time.sleep(delay)
            delay *= 2  # Exponential backoff
 
        except ClientError as e:
            logger.error(
                f"Kinesis error for {partition_key}: "
                f"{e.response['Error']['Code']}: {e.response['Error']['Message']}"
            )
            return False
 
    logger.error(f"Failed to publish record for {partition_key} after {MAX_RETRIES} retries")
    return False
 
 
def print_startup_banner(mode: str, duration: int | None, interval: float) -> None:
    """Print a clear startup summary so the user knows the producer is running."""
    print("\n" + "=" * 60)
    print("  Real-Time Streaming Analytics — IoT Sensor Producer")
    print("=" * 60)
    print(f"  Stream   : {STREAM_NAME}")
    print(f"  Region   : {REGION}")
    print(f"  Mode     : {mode.upper()}")
    print(f"  Sensors  : {len(SENSORS)}")
    print(f"  Interval : {interval}s per batch")
    print(f"  Duration : {'Until Ctrl+C' if duration is None else f'{duration}s'}")
    if mode == "anomaly":
        print(f"\n  ⚠ ANOMALY SENSOR : {ANOMALY_SENSOR_ID}")
        print(f"  ⚠ TEMP RANGE     : {ANOMALY_TEMP_RANGE[0]}–{ANOMALY_TEMP_RANGE[1]}°C")
        print(f"  ⚠ ALERT THRESHOLD: 90°C (5-min avg will trigger SNS)")
    print("=" * 60)
    print("  Press Ctrl+C to stop\n")
 
 
# ---------------------------------------------------------------------------
# Main Producer Loop
# ---------------------------------------------------------------------------
 
def run_producer(mode: str, duration: int | None, interval: float) -> None:
    """
    Main producer loop. Generates and publishes sensor readings at a
    fixed interval until the duration expires or Ctrl+C is pressed.
 
    Args:
        mode     : 'normal' or 'anomaly'
        duration : Total seconds to run, or None to run indefinitely.
        interval : Seconds between each full batch of sensor readings.
    """
    client      = boto3.client("kinesis", region_name=REGION)
    anomaly_mode = (mode == "anomaly")
 
    print_startup_banner(mode, duration, interval)
 
    start_time     = time.time()
    total_sent     = 0
    total_failed   = 0
    batch_number   = 0
 
    try:
        while True:
            # Check duration limit
            if duration and (time.time() - start_time) >= duration:
                logger.info(f"Duration of {duration}s reached — stopping producer")
                break
 
            batch_number += 1
            batch_sent   = 0
            batch_failed = 0
 
            # Publish one reading per sensor per interval
            for sensor in SENSORS:
                reading = generate_sensor_reading(sensor, anomaly_mode)
                success = put_record_with_retry(
                    client,
                    STREAM_NAME,
                    reading,
                    partition_key=sensor["sensor_id"],
                )
 
                if success:
                    batch_sent += 1
                    # Console output — visible progress for the user
                    status_icon = "🌡" if reading["temperature"] < 90 else "🚨"
                    print(
                        f"  {status_icon} Batch {batch_number:04d} | "
                        f"{sensor['sensor_id']} | "
                        f"temp={reading['temperature']:5.1f}°C | "
                        f"pressure={reading['pressure']:.1f}hPa | "
                        f"humidity={reading['humidity']:.1f}%"
                    )
                else:
                    batch_failed += 1
 
            total_sent   += batch_sent
            total_failed += batch_failed
 
            # Summary line every 10 batches
            if batch_number % 10 == 0:
                elapsed = int(time.time() - start_time)
                print(
                    f"\n  📊 Progress | batches={batch_number} | "
                    f"records_sent={total_sent} | "
                    f"failed={total_failed} | "
                    f"elapsed={elapsed}s\n"
                )
 
            time.sleep(interval)
 
    except KeyboardInterrupt:
        print("\n\n  Producer stopped by user (Ctrl+C)")
 
    finally:
        # Final summary
        elapsed = int(time.time() - start_time)
        print("\n" + "=" * 60)
        print("  Producer Session Summary")
        print("=" * 60)
        print(f"  Total batches : {batch_number}")
        print(f"  Records sent  : {total_sent}")
        print(f"  Records failed: {total_failed}")
        print(f"  Elapsed time  : {elapsed}s")
        print(f"  Mode          : {mode.upper()}")
        print("=" * 60 + "\n")
 
 
# ---------------------------------------------------------------------------
# CLI Argument Parser
# ---------------------------------------------------------------------------
 
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="IoT Sensor Data Producer for Real-Time Streaming Analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python producer.py                        # Normal mode, runs until Ctrl+C
  python producer.py --mode anomaly         # Spike sensor-floor-A-01 above 90C
  python producer.py --duration 120         # Run for 2 minutes then stop
  python producer.py --mode anomaly --duration 300  # Anomaly for 5 minutes
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["normal", "anomaly"],
        default="normal",
        help="normal: healthy readings | anomaly: spikes one sensor above 90C threshold",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="How many seconds to run before stopping (default: run until Ctrl+C)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between each batch of sensor readings (default: 1.0)",
    )
    return parser.parse_args()
 
 
# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
 
if __name__ == "__main__":
    args = parse_args()
    run_producer(
        mode=args.mode,
        duration=args.duration,
        interval=args.interval,
    )