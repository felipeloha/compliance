resource "aws_cloudwatch_event_rule" "daily_reconciliation" {
  name                = "${var.name_prefix}-daily-reconciliation"
  description         = "Daily reconciliation of customer data access"
  schedule_expression = var.daily_reconciliation_cron
  tags                = var.tags
}

resource "aws_cloudwatch_event_target" "reconciliation_lambda" {
  rule      = aws_cloudwatch_event_rule.daily_reconciliation.name
  target_id = "DailyReconciliationLambda"
  arn       = aws_lambda_function.daily_reconciliation.arn
}

resource "aws_lambda_permission" "daily_reconciliation_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.daily_reconciliation.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_reconciliation.arn
}

resource "aws_lambda_permission" "logs_invoke_audit_forwarder_postgresql" {
  statement_id  = "AllowCloudWatchLogsInvokeAuditForwarder"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.audit_log_ctl_forwarder.function_name
  principal     = "logs.${var.aws_region}.amazonaws.com"
  source_arn    = "arn:aws:logs:${var.aws_region}:${var.account_id}:log-group:${var.rds_postgresql_loggroup_name}:*"
}

## NOTE: CloudWatch Logs allows only a single subscription filter per log group effectively.
## We keep one broad filter (postgresql_connections) that captures general activity lines
## containing user@db prefixes. The forwarder parses both connect and disconnect events from
## these lines as needed.
resource "aws_cloudwatch_log_subscription_filter" "postgresql_connections" {
  name           = "${var.name_prefix}-pg-connections-filter-v3"
  log_group_name = var.rds_postgresql_loggroup_name
  # Use a single regex with OR per AWS docs to match PG connect/disconnect/activity
  # Docs: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html
  # - "connection authorized" (connect)
  # - "disconnection:" (disconnect)
  # - user@db prefix lines ending with ':' (activity)
  filter_pattern  = "%connection authorized|disconnection:|.*@.*:%"
  destination_arn = aws_lambda_function.audit_log_ctl_forwarder.arn

  depends_on = [aws_lambda_permission.logs_invoke_audit_forwarder_postgresql]
}

# Alarms for audit forwarder
resource "aws_cloudwatch_metric_alarm" "audit_forwarder_errors" {
  alarm_name          = "${var.name_prefix}-forwarder-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Audit forwarder Lambda function errors"
  alarm_actions       = var.cw_metric_alarm_actions

  dimensions = {
    FunctionName = aws_lambda_function.audit_log_ctl_forwarder.function_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "slack_handler_errors" {
  alarm_name          = "${var.name_prefix}-slack-handler-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Slack access request handler Lambda function errors"
  alarm_actions       = var.cw_metric_alarm_actions

  dimensions = {
    FunctionName = aws_lambda_function.slack_access_request_handler.function_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "daily_reconciliation_errors" {
  alarm_name          = "${var.name_prefix}-daily-reconciliation-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Daily reconciliation Lambda function errors"
  alarm_actions       = var.cw_metric_alarm_actions

  dimensions = {
    FunctionName = aws_lambda_function.daily_reconciliation.function_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "audit_forwarder_duration" {
  alarm_name          = "${var.name_prefix}-forwarder-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 250000
  alarm_description   = "Audit forwarder Lambda function duration"
  alarm_actions       = var.cw_metric_alarm_actions

  dimensions = {
    FunctionName = aws_lambda_function.audit_log_ctl_forwarder.function_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_write_capacity_alarm" {
  alarm_name          = "${var.name_prefix}-dynamodb-write-capacity"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ConsumedWriteCapacityUnits"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 1000
  alarm_description   = "Alarm when DynamoDB write capacity consumption is high"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.cw_metric_alarm_actions

  dimensions = {
    TableName = aws_dynamodb_table.access_requests.name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_read_capacity_alarm" {
  alarm_name          = "${var.name_prefix}-dynamodb-read-capacity"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ConsumedReadCapacityUnits"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 1000
  alarm_description   = "Alarm when DynamoDB read capacity consumption is high"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.cw_metric_alarm_actions

  dimensions = {
    TableName = aws_dynamodb_table.access_requests.name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_system_errors_alarm" {
  alarm_name          = "${var.name_prefix}-dynamodb-system-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "SystemErrors"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Alarm when DynamoDB system errors occur"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.cw_metric_alarm_actions

  dimensions = {
    TableName = aws_dynamodb_table.access_requests.name
  }

  tags = var.tags
}
