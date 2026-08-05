# --- Alarm 1: Low Quality Score ---
# Fires when the minimum quality score across all checked files
# drops below 50% in a 5-minute window. A score below 50%
# indicates more than half the records have quality issues —
# the batch must not proceed to the clinical database.
resource "aws_cloudwatch_metric_alarm" "low_quality_score" {
  alarm_name          = "project3-patient-data-quality-low-score-alarm"
  alarm_description   = "Quality score dropped below 50% — patient data requires immediate review"
  namespace           = "HealthcareDataQuality"
  metric_name         = "QualityScore"
  dimensions = {
    SourceFile = "patient_records_batch_001.csv"
  }
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 50
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.quality_alerts.arn]
}

# --- Alarm 2: Critical Issues Detected ---
# Fires when any critical issue is detected in patient records.
# Critical issues include missing MRN, impossible vital signs,
# and discharge before admission — all patient safety risks.
resource "aws_cloudwatch_metric_alarm" "critical_issues" {
  alarm_name          = "project3-patient-data-quality-critical-issues-alarm"
  alarm_description   = "Critical data quality issues detected in patient records — immediate clinical review required"
  namespace           = "HealthcareDataQuality"
  metric_name         = "CriticalIssues"
  dimensions = {
    SourceFile = "patient_records_batch_001.csv"
  }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.quality_alerts.arn]
}

# --- Alarm 3: Duplicate MRNs Detected ---
# Fires when any duplicate Medical Record Numbers are found.
# Duplicate MRNs mean the same patient has multiple charts —
# medications and lab results split across records creates
# serious patient safety risks.
resource "aws_cloudwatch_metric_alarm" "duplicate_mrns" {
  alarm_name          = "project3-patient-data-quality-duplicate-mrns-alarm"
  alarm_description   = "Duplicate Medical Record Numbers detected — patient safety risk requires immediate deduplication"
  namespace           = "HealthcareDataQuality"
  metric_name         = "DuplicateMRNs"
  dimensions = {
    SourceFile = "patient_records_batch_001.csv"
  }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.quality_alerts.arn]
}

# --- CloudWatch Dashboard ---
# Single-pane-of-glass view of the entire patient data quality pipeline.
# Dashboard JSON mirrors exactly what was built and verified in the console.
resource "aws_cloudwatch_dashboard" "patient_data_quality" {
  dashboard_name = "project3-patient-data-quality-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 2
        properties = {
          markdown = "# 🏥 Patient Data Quality Dashboard\n**Scenario:** Regional hospital network migrating patient records from legacy EHR system. This dashboard monitors automated quality checks on every incoming patient data batch.\n\n**Quality Engine:** `patient-data-quality-engine` | **Namespace:** `HealthcareDataQuality` | **Region:** `us-east-1`"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 2
        width  = 8
        height = 6
        properties = {
          title  = "Quality Score (%)"
          view   = "singleValue"
          region = "us-east-1"
          metrics = [
            ["HealthcareDataQuality", "QualityScore", "SourceFile", "patient_records_batch_001.csv", { stat = "Minimum", period = 300 }]
          ]
          setPeriodToTimeRange = true
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 2
        width  = 8
        height = 6
        properties = {
          title  = "Total Records Processed"
          view   = "singleValue"
          region = "us-east-1"
          metrics = [
            ["HealthcareDataQuality", "TotalRecords", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300 }]
          ]
          setPeriodToTimeRange = true
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 2
        width  = 8
        height = 6
        properties = {
          title  = "Critical Issues Detected"
          view   = "singleValue"
          region = "us-east-1"
          metrics = [
            ["HealthcareDataQuality", "CriticalIssues", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300 }]
          ]
          setPeriodToTimeRange = true
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 8
        width  = 12
        height = 6
        properties = {
          title  = "Quality Score Over Time"
          view   = "timeSeries"
          region = "us-east-1"
          metrics = [
            ["HealthcareDataQuality", "QualityScore", "SourceFile", "patient_records_batch_001.csv", { stat = "Minimum", period = 300, color = "#2ca02c" }]
          ]
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
          annotations = {
            horizontal = [
              {
                label = "Minimum Acceptable Quality"
                value = 50
                color = "#d62728"
              }
            ]
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 8
        width  = 12
        height = 6
        properties = {
          title  = "Issues by Category"
          view   = "timeSeries"
          region = "us-east-1"
          metrics = [
            ["HealthcareDataQuality", "CriticalIssues", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300, label = "Critical Issues", color = "#d62728" }],
            ["HealthcareDataQuality", "DuplicateMRNs", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300, label = "Duplicate MRNs", color = "#ff7f0e" }],
            ["HealthcareDataQuality", "MissingFieldIssues", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300, label = "Missing Fields", color = "#9467bd" }],
            ["HealthcareDataQuality", "SchemaViolations", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300, label = "Schema Violations", color = "#8c564b" }],
            ["HealthcareDataQuality", "VitalSignAnomalies", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300, label = "Vital Anomalies", color = "#e377c2" }],
            ["HealthcareDataQuality", "BusinessRuleViolations", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300, label = "Business Rule Violations", color = "#7f7f7f" }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 14
        width  = 6
        height = 6
        properties = {
          title  = "Duplicate MRNs"
          view   = "singleValue"
          region = "us-east-1"
          metrics = [
            ["HealthcareDataQuality", "DuplicateMRNs", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300 }]
          ]
          setPeriodToTimeRange = true
        }
      },
      {
        type   = "metric"
        x      = 6
        y      = 14
        width  = 6
        height = 6
        properties = {
          title  = "Missing Clinical Fields"
          view   = "singleValue"
          region = "us-east-1"
          metrics = [
            ["HealthcareDataQuality", "MissingFieldIssues", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300 }]
          ]
          setPeriodToTimeRange = true
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 14
        width  = 6
        height = 6
        properties = {
          title  = "Vital Sign Anomalies"
          view   = "singleValue"
          region = "us-east-1"
          metrics = [
            ["HealthcareDataQuality", "VitalSignAnomalies", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300 }]
          ]
          setPeriodToTimeRange = true
        }
      },
      {
        type   = "metric"
        x      = 18
        y      = 14
        width  = 6
        height = 6
        properties = {
          title  = "Business Rule Violations"
          view   = "singleValue"
          region = "us-east-1"
          metrics = [
            ["HealthcareDataQuality", "BusinessRuleViolations", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300 }]
          ]
          setPeriodToTimeRange = true
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 20
        width  = 24
        height = 4
        properties = {
          title  = "Pipeline Alarm Status — Quality Score vs Thresholds"
          view   = "timeSeries"
          region = "us-east-1"
          metrics = [
            ["HealthcareDataQuality", "QualityScore", "SourceFile", "patient_records_batch_001.csv", { stat = "Minimum", period = 300, label = "Quality Score", color = "#2ca02c" }],
            ["HealthcareDataQuality", "CriticalIssues", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300, label = "Critical Issues", color = "#d62728" }],
            ["HealthcareDataQuality", "DuplicateMRNs", "SourceFile", "patient_records_batch_001.csv", { stat = "Maximum", period = 300, label = "Duplicate MRNs", color = "#ff7f0e" }]
          ]
          annotations = {
            horizontal = [
              {
                label = "Quality Score Minimum Threshold"
                value = 50
                color = "#d62728"
              }
            ]
          }
        }
      }
    ]
  })
}
