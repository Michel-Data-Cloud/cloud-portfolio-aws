# --- Patient Data Quality Alerts SNS Topic ---
resource "aws_sns_topic" "quality_alerts" {
  name         = "project3-patient-data-quality-alerts-sns-topic"
  display_name = "Patient Data Quality Alerts"
}

# --- Email Subscription ---
# Note: Terraform creates the subscription but cannot confirm it.
# A confirmation email will be sent to the address below.
# The subscriber must click the confirmation link before alerts deliver.
resource "aws_sns_topic_subscription" "quality_alerts_email" {
  topic_arn = aws_sns_topic.quality_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
