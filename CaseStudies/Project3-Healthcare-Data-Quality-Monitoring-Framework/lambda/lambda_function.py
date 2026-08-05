"""
Patient Data Quality Engine
===========================
Scenario : Regional hospital network migrating patient records
           from a legacy EHR system to a cloud-based data platform.
Purpose  : Detect data quality problems before they reach the
           clinical database and create patient safety risks.

Quality Check Categories
------------------------
1. Missing critical fields   — required clinical fields absent
2. Schema violations         — wrong data types or formats
3. Out-of-range vital signs  — physiologically impossible values
4. Business rule violations  — logical inconsistencies in the data
5. Duplicate detection       — same MRN appearing multiple times
6. Data freshness            — stale records from failed batch

Output
------
- JSON quality report written to S3 results bucket
- HTML quality report written to S3 results bucket
- CloudWatch custom metrics published
"""

import json
import boto3
import csv
import io
import os
from datetime import datetime, timezone
from collections import defaultdict

# --- AWS Clients ---
s3 = boto3.client("s3")
cw = boto3.client("cloudwatch")

# --- Environment Variables ---
RESULTS_BUCKET  = os.environ.get("RESULTS_BUCKET", "project3-patient-quality-results-june2026")
FRESHNESS_HOURS = int(os.environ.get("FRESHNESS_HOURS", "24"))

# --- Clinical Constants ---
VITAL_SIGN_RANGES = {
    "heart_rate_bpm":        {"min": 20,   "max": 300},
    "systolic_bp_mmhg":      {"min": 50,   "max": 300},
    "diastolic_bp_mmhg":     {"min": 20,   "max": 200},
    "temperature_celsius":   {"min": 30.0, "max": 45.0},
    "oxygen_saturation_pct": {"min": 50,   "max": 100},
    "respiratory_rate_bpm":  {"min": 4,    "max": 60},
}

CRITICAL_FIELDS = [
    "patient_id",
    "mrn",
    "date_of_birth",
    "admission_date",
    "primary_diagnosis",
    "attending_physician",
]

SCHEMA_RULES = {
    "patient_id":            str,
    "mrn":                   str,
    "date_of_birth":         "date",
    "admission_date":        "date",
    "discharge_date":        "date",
    "heart_rate_bpm":        int,
    "systolic_bp_mmhg":      int,
    "diastolic_bp_mmhg":     int,
    "temperature_celsius":   float,
    "oxygen_saturation_pct": int,
    "respiratory_rate_bpm":  int,
}


# ================================================================
# QUALITY CHECK FUNCTIONS
# ================================================================

def check_missing_critical_fields(record: dict, row_num: int) -> list:
    issues = []
    for field in CRITICAL_FIELDS:
        if not record.get(field, "").strip():
            issues.append({
                "check":      "missing_critical_field",
                "row":        row_num,
                "field":      field,
                "severity":   "CRITICAL",
                "message":    f"Required clinical field '{field}' is missing or empty",
                "patient_id": record.get("patient_id", "UNKNOWN"),
            })
    return issues


def check_schema_violations(record: dict, row_num: int) -> list:
    issues = []
    for field, expected_type in SCHEMA_RULES.items():
        value = record.get(field, "").strip()
        if not value:
            continue
        if expected_type == "date":
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                issues.append({
                    "check":      "schema_violation",
                    "row":        row_num,
                    "field":      field,
                    "value":      value,
                    "severity":   "HIGH",
                    "message":    f"Field '{field}' value '{value}' is not a valid YYYY-MM-DD date",
                    "patient_id": record.get("patient_id", "UNKNOWN"),
                })
        elif expected_type == int:
            try:
                int(value)
            except ValueError:
                issues.append({
                    "check":      "schema_violation",
                    "row":        row_num,
                    "field":      field,
                    "value":      value,
                    "severity":   "HIGH",
                    "message":    f"Field '{field}' value '{value}' must be an integer",
                    "patient_id": record.get("patient_id", "UNKNOWN"),
                })
        elif expected_type == float:
            try:
                float(value)
            except ValueError:
                issues.append({
                    "check":      "schema_violation",
                    "row":        row_num,
                    "field":      field,
                    "value":      value,
                    "severity":   "HIGH",
                    "message":    f"Field '{field}' value '{value}' must be a number",
                    "patient_id": record.get("patient_id", "UNKNOWN"),
                })
    return issues


def check_vital_sign_ranges(record: dict, row_num: int) -> list:
    issues = []
    for field, bounds in VITAL_SIGN_RANGES.items():
        value_str = record.get(field, "").strip()
        if not value_str:
            continue
        try:
            value = float(value_str)
            if value < bounds["min"] or value > bounds["max"]:
                issues.append({
                    "check":      "vital_sign_out_of_range",
                    "row":        row_num,
                    "field":      field,
                    "value":      value,
                    "valid_min":  bounds["min"],
                    "valid_max":  bounds["max"],
                    "severity":   "CRITICAL",
                    "message":    (
                        f"Vital sign '{field}' value {value} is outside "
                        f"physiological range [{bounds['min']} – {bounds['max']}]"
                    ),
                    "patient_id": record.get("patient_id", "UNKNOWN"),
                })
        except ValueError:
            pass
    return issues


def check_business_rules(record: dict, row_num: int) -> list:
    issues = []
    admission_str = record.get("admission_date",  "").strip()
    discharge_str = record.get("discharge_date",  "").strip()
    dob_str       = record.get("date_of_birth",   "").strip()

    if admission_str and discharge_str:
        try:
            admission = datetime.strptime(admission_str, "%Y-%m-%d")
            discharge = datetime.strptime(discharge_str, "%Y-%m-%d")
            if discharge < admission:
                issues.append({
                    "check":          "business_rule_violation",
                    "row":            row_num,
                    "rule":           "discharge_before_admission",
                    "severity":       "CRITICAL",
                    "admission_date": admission_str,
                    "discharge_date": discharge_str,
                    "message":        (
                        f"Discharge date {discharge_str} precedes "
                        f"admission date {admission_str}"
                    ),
                    "patient_id": record.get("patient_id", "UNKNOWN"),
                })
        except ValueError:
            pass

    if dob_str and admission_str:
        try:
            dob       = datetime.strptime(dob_str,       "%Y-%m-%d")
            admission = datetime.strptime(admission_str, "%Y-%m-%d")
            if admission < dob:
                issues.append({
                    "check":          "business_rule_violation",
                    "row":            row_num,
                    "rule":           "admission_before_birth",
                    "severity":       "CRITICAL",
                    "date_of_birth":  dob_str,
                    "admission_date": admission_str,
                    "message":        (
                        f"Admission date {admission_str} precedes "
                        f"date of birth {dob_str}"
                    ),
                    "patient_id": record.get("patient_id", "UNKNOWN"),
                })
        except ValueError:
            pass

    if dob_str:
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d")
            age = (datetime.now() - dob).days / 365.25
            if age < 0 or age > 130:
                issues.append({
                    "check":         "business_rule_violation",
                    "row":           row_num,
                    "rule":          "unrealistic_age",
                    "severity":      "HIGH",
                    "date_of_birth": dob_str,
                    "computed_age":  round(age, 1),
                    "message":       f"Computed patient age {round(age,1)} years is unrealistic",
                    "patient_id":    record.get("patient_id", "UNKNOWN"),
                })
        except ValueError:
            pass

    return issues


def check_duplicates(records: list) -> list:
    issues    = []
    mrn_index = defaultdict(list)
    for i, record in enumerate(records, start=2):
        mrn = record.get("mrn", "").strip()
        if mrn:
            mrn_index[mrn].append({
                "row":        i,
                "patient_id": record.get("patient_id", "UNKNOWN"),
            })
    for mrn, occurrences in mrn_index.items():
        if len(occurrences) > 1:
            issues.append({
                "check":       "duplicate_mrn",
                "mrn":         mrn,
                "severity":    "CRITICAL",
                "occurrences": occurrences,
                "count":       len(occurrences),
                "message":     (
                    f"MRN '{mrn}' appears {len(occurrences)} times — "
                    f"duplicate patient records detected"
                ),
            })
    return issues


def check_data_freshness(s3_key: str, s3_bucket: str) -> list:
    issues = []
    try:
        response      = s3.head_object(Bucket=s3_bucket, Key=s3_key)
        last_modified = response["LastModified"]
        age_hours     = (
            datetime.now(timezone.utc) - last_modified
        ).total_seconds() / 3600
        if age_hours > FRESHNESS_HOURS:
            issues.append({
                "check":           "stale_data",
                "severity":        "HIGH",
                "file":            s3_key,
                "age_hours":       round(age_hours, 2),
                "threshold_hours": FRESHNESS_HOURS,
                "message":         (
                    f"Patient data file is {round(age_hours,2)} hours old — "
                    f"exceeds freshness threshold of {FRESHNESS_HOURS} hours"
                ),
            })
    except Exception as e:
        issues.append({
            "check":    "stale_data",
            "severity": "LOW",
            "message":  f"Could not determine file age: {str(e)}",
        })
    return issues


# ================================================================
# HTML REPORT GENERATOR
# ================================================================

def generate_html_report(report: dict) -> str:
    """Generate a human-readable HTML quality report.
    Designed for hospital data quality managers who need
    a clear, color-coded summary they can open in a browser
    and forward to the clinical informatics team.
    """
    summary  = report["summary"]
    issues   = report["issues"]
    metadata = report["report_metadata"]

    # Color-code the quality score
    score = summary["quality_score"]
    if score >= 80:
        score_color = "#2ca02c"
        score_label = "GOOD"
    elif score >= 50:
        score_color = "#ff7f0e"
        score_label = "WARNING"
    else:
        score_color = "#d62728"
        score_label = "CRITICAL"

    # Build issues table rows
    issue_rows = ""
    for issue in issues:
        severity = issue.get("severity", "LOW")
        if severity == "CRITICAL":
            row_color = "#ffd7d7"
        elif severity == "HIGH":
            row_color = "#fff3cd"
        else:
            row_color = "#ffffff"

        issue_rows += f"""
        <tr style="background-color: {row_color};">
            <td>{issue.get('patient_id', 'N/A')}</td>
            <td>{issue.get('row', 'N/A')}</td>
            <td><span class="badge badge-{severity.lower()}">{severity}</span></td>
            <td>{issue.get('check', 'N/A').replace('_', ' ').title()}</td>
            <td>{issue.get('message', 'N/A')}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Patient Data Quality Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #1a5276, #2980b9);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 24px;
        }}
        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 24px;
        }}
        .header p {{
            margin: 4px 0;
            opacity: 0.85;
            font-size: 14px;
        }}
        .score-card {{
            background: white;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 24px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .score-value {{
            font-size: 72px;
            font-weight: bold;
            color: {score_color};
            line-height: 1;
        }}
        .score-label {{
            font-size: 20px;
            font-weight: bold;
            color: {score_color};
            margin-top: 8px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .metric-card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 36px;
            font-weight: bold;
            color: #1a5276;
        }}
        .metric-value.alert {{
            color: #d62728;
        }}
        .metric-label {{
            font-size: 13px;
            color: #666;
            margin-top: 4px;
        }}
        .section {{
            background: white;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            margin: 0 0 16px 0;
            font-size: 18px;
            color: #1a5276;
            border-bottom: 2px solid #2980b9;
            padding-bottom: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th {{
            background-color: #1a5276;
            color: white;
            padding: 10px 12px;
            text-align: left;
        }}
        td {{
            padding: 8px 12px;
            border-bottom: 1px solid #eee;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        }}
        .badge-critical {{
            background-color: #d62728;
            color: white;
        }}
        .badge-high {{
            background-color: #ff7f0e;
            color: white;
        }}
        .badge-low {{
            background-color: #7f7f7f;
            color: white;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 24px;
        }}
    </style>
</head>
<body>

<div class="header">
    <h1>🏥 Patient Data Quality Report</h1>
    <p><strong>Scenario:</strong> EHR Legacy Migration — Regional Hospital Network</p>
    <p><strong>Source File:</strong> {metadata['source_file']}</p>
    <p><strong>Generated:</strong> {metadata['generated_at']}</p>
    <p><strong>Quality Engine:</strong> {metadata['quality_engine']}</p>
</div>

<div class="score-card">
    <div class="score-value">{score}%</div>
    <div class="score-label">Overall Quality Score — {score_label}</div>
</div>

<div class="metrics-grid">
    <div class="metric-card">
        <div class="metric-value">{summary['total_records']}</div>
        <div class="metric-label">Total Records</div>
    </div>
    <div class="metric-card">
        <div class="metric-value {'alert' if summary['total_issues'] > 0 else ''}">{summary['total_issues']}</div>
        <div class="metric-label">Total Issues</div>
    </div>
    <div class="metric-card">
        <div class="metric-value {'alert' if summary['critical_issues'] > 0 else ''}">{summary['critical_issues']}</div>
        <div class="metric-label">Critical Issues</div>
    </div>
    <div class="metric-card">
        <div class="metric-value {'alert' if summary['duplicate_mrns'] > 0 else ''}">{summary['duplicate_mrns']}</div>
        <div class="metric-label">Duplicate MRNs</div>
    </div>
    <div class="metric-card">
        <div class="metric-value {'alert' if summary['missing_fields'] > 0 else ''}">{summary['missing_fields']}</div>
        <div class="metric-label">Missing Fields</div>
    </div>
    <div class="metric-card">
        <div class="metric-value {'alert' if summary['schema_violations'] > 0 else ''}">{summary['schema_violations']}</div>
        <div class="metric-label">Schema Violations</div>
    </div>
    <div class="metric-card">
        <div class="metric-value {'alert' if summary['vital_anomalies'] > 0 else ''}">{summary['vital_anomalies']}</div>
        <div class="metric-label">Vital Anomalies</div>
    </div>
    <div class="metric-card">
        <div class="metric-value {'alert' if summary['business_rule_violations'] > 0 else ''}">{summary['business_rule_violations']}</div>
        <div class="metric-label">Business Rule Violations</div>
    </div>
</div>

<div class="section">
    <h2>📋 Issue Detail</h2>
    <table>
        <thead>
            <tr>
                <th>Patient ID</th>
                <th>Row</th>
                <th>Severity</th>
                <th>Check Type</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>
            {issue_rows}
        </tbody>
    </table>
</div>

<div class="footer">
    <p>Generated by Patient Data Quality Engine v1.0 | AWS Lambda + CloudWatch | Project 3 — Healthcare Data Quality Framework</p>
    <p>⚠️ This report contains synthetic data for portfolio demonstration purposes only. No real patient data was used.</p>
</div>

</body>
</html>"""

    return html


# ================================================================
# METRICS PUBLISHER
# ================================================================

def publish_quality_metrics(summary: dict, file_name: str) -> None:
    namespace  = "HealthcareDataQuality"
    dimensions = [{"Name": "SourceFile", "Value": file_name}]

    metrics = [
        ("TotalRecords",             summary["total_records"],            "Count"),
        ("TotalIssues",              summary["total_issues"],             "Count"),
        ("CriticalIssues",           summary["critical_issues"],          "Count"),
        ("QualityScore",             summary["quality_score"],            "Percent"),
        ("DuplicateMRNs",            summary["duplicate_mrns"],           "Count"),
        ("MissingFieldIssues",       summary["missing_fields"],           "Count"),
        ("SchemaViolations",         summary["schema_violations"],        "Count"),
        ("VitalSignAnomalies",       summary["vital_anomalies"],          "Count"),
        ("BusinessRuleViolations",   summary["business_rule_violations"], "Count"),
        ("StaleDataIssues",          summary["stale_data_issues"],        "Count"),
    ]

    metric_data = [
        {
            "MetricName": name,
            "Dimensions": dimensions,
            "Value":      value,
            "Unit":       unit,
        }
        for name, value, unit in metrics
    ]

    cw.put_metric_data(Namespace=namespace, MetricData=metric_data)
    print(f"[METRICS] Published {len(metric_data)} metrics to CloudWatch namespace '{namespace}'")


# ================================================================
# LAMBDA HANDLER
# ================================================================

def lambda_handler(event, context):
    print(f"[START] Patient Data Quality Engine invoked")
    print(f"[EVENT] {json.dumps(event)}")

    # --- Parse S3 trigger event ---
    record     = event["Records"][0]
    src_bucket = record["s3"]["bucket"]["name"]
    s3_key     = record["s3"]["object"]["key"]
    file_name  = s3_key.split("/")[-1]

    print(f"[INPUT] Bucket: {src_bucket} | Key: {s3_key}")

    # --- Read CSV from S3 ---
    response  = s3.get_object(Bucket=src_bucket, Key=s3_key)
    csv_bytes = response["Body"].read().decode("utf-8")
    reader    = csv.DictReader(io.StringIO(csv_bytes))
    records   = list(reader)

    print(f"[PARSE] Loaded {len(records)} patient records from {file_name}")

    # --- Run all quality checks ---
    all_issues = []
    all_issues += check_data_freshness(s3_key, src_bucket)
    all_issues += check_duplicates(records)
    for row_num, record in enumerate(records, start=2):
        all_issues += check_missing_critical_fields(record, row_num)
        all_issues += check_schema_violations(record, row_num)
        all_issues += check_vital_sign_ranges(record, row_num)
        all_issues += check_business_rules(record, row_num)

    # --- Build quality summary ---
    critical_issues = [i for i in all_issues if i.get("severity") == "CRITICAL"]
    quality_score   = round(
        max(0, (1 - len(all_issues) / max(len(records), 1)) * 100), 2
    )

    summary = {
        "total_records":            len(records),
        "total_issues":             len(all_issues),
        "critical_issues":          len(critical_issues),
        "quality_score":            quality_score,
        "duplicate_mrns":           len([i for i in all_issues if i.get("check") == "duplicate_mrn"]),
        "missing_fields":           len([i for i in all_issues if i.get("check") == "missing_critical_field"]),
        "schema_violations":        len([i for i in all_issues if i.get("check") == "schema_violation"]),
        "vital_anomalies":          len([i for i in all_issues if i.get("check") == "vital_sign_out_of_range"]),
        "business_rule_violations": len([i for i in all_issues if i.get("check") == "business_rule_violation"]),
        "stale_data_issues":        len([i for i in all_issues if i.get("check") == "stale_data"]),
    }

    # --- Build full quality report ---
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report = {
        "report_metadata": {
            "generated_at":   datetime.now(timezone.utc).isoformat(),
            "source_bucket":  src_bucket,
            "source_file":    s3_key,
            "quality_engine": "patient-data-quality-engine v1.0",
            "scenario":       "EHR Legacy Migration — Regional Hospital Network",
        },
        "summary": summary,
        "issues":  all_issues,
    }

    # --- Write JSON report ---
    json_key = f"quality-reports/{file_name.replace('.csv','')}_report_{timestamp}.json"
    s3.put_object(
        Bucket      = RESULTS_BUCKET,
        Key         = json_key,
        Body        = json.dumps(report, indent=2, default=str),
        ContentType = "application/json",
    )
    print(f"[JSON REPORT] Written to s3://{RESULTS_BUCKET}/{json_key}")

    # --- Write HTML report ---
    html_content = generate_html_report(report)
    html_key     = f"quality-reports/{file_name.replace('.csv','')}_report_{timestamp}.html"
    s3.put_object(
        Bucket      = RESULTS_BUCKET,
        Key         = html_key,
        Body        = html_content,
        ContentType = "text/html",
    )
    print(f"[HTML REPORT] Written to s3://{RESULTS_BUCKET}/{html_key}")

    # --- Publish CloudWatch metrics ---
    publish_quality_metrics(summary, file_name)

    # --- Final log summary ---
    print(f"[SUMMARY] Records: {summary['total_records']} | "
          f"Issues: {summary['total_issues']} | "
          f"Critical: {summary['critical_issues']} | "
          f"Quality Score: {summary['quality_score']}%")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message":    "Quality check complete",
            "json_report": json_key,
            "html_report": html_key,
            "summary":    summary,
        }),
    }
