data "archive_file" "slack_access_request_handler" {
  type        = "zip"
  source_file = "${path.module}/lambda/slack_access_request_handler.py"
  output_path = "${path.module}/build/slack_access_request_handler.zip"
}

data "archive_file" "daily_reconciliation" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/build/daily_reconciliation.zip"
  excludes = [
    "test_*.py",
    "test_env/",
    "__pycache__/",
    "*.pyc"
  ]
}

data "archive_file" "audit_log_ctl_forwarder" {
  type        = "zip"
  source_file = "${path.module}/lambda/audit_log_ctl_forwarder.py"
  output_path = "${path.module}/build/audit_log_ctl_forwarder.zip"
}

data "aws_cloudwatch_event_bus" "default" {
  name = "default"
}

resource "aws_lambda_function" "slack_access_request_handler" {
  filename         = data.archive_file.slack_access_request_handler.output_path
  function_name    = "${var.name_prefix}-slack-access-request-handler"
  role             = aws_iam_role.lambda_role.arn
  handler          = "slack_access_request_handler.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.slack_lambda_timeout
  memory_size      = var.slack_lambda_memory_mb
  source_code_hash = data.archive_file.slack_access_request_handler.output_base64sha256

  environment {
    variables = {
      SLACK_SIGNING_SECRET_PARAM_NAME = aws_ssm_parameter.slack_signing_secret.name
      SLACK_BOT_TOKEN_PARAM_NAME      = aws_ssm_parameter.slack_bot_token.name
      DYNAMODB_TABLE_NAME             = aws_dynamodb_table.access_requests.name
      ALLOWED_DURATIONS_PARAM         = aws_ssm_parameter.config_allowed_durations.name
      LOCAL_TIMEZONE                  = var.local_timezone
      ACCESS_REQUEST_RETENTION_YEARS  = var.access_request_retention_years
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-slack-access-request-handler"
  })
}

resource "aws_lambda_function" "daily_reconciliation" {
  filename         = data.archive_file.daily_reconciliation.output_path
  function_name    = "${var.name_prefix}-daily-reconciliation"
  role             = aws_iam_role.lambda_role.arn
  handler          = "daily_reconciliation.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.reconciliation_lambda_timeout
  memory_size      = var.reconciliation_lambda_memory_mb
  source_code_hash = data.archive_file.daily_reconciliation.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE_NAME                 = aws_dynamodb_table.access_requests.name
      CLOUDTRAIL_LAKE_EVENT_DATA_STORE_ID = var.cloudtrail_lake_event_data_store_id
      CLOUDTRAIL_LAKE_CURATED_STORE_ID    = var.cloudtrail_lake_curated_store_id
      CUSTOMER_DATA_CONFIG_PARAM          = aws_ssm_parameter.config_customer_data.name
      WHITELIST_DB_USERS_PARAM            = aws_ssm_parameter.config_whitelist_db_users.name
      WHITELIST_S3_ACTORS_PARAM           = aws_ssm_parameter.config_whitelist_s3_actors.name
      JIRA_REPORTING_ENABLED_PARAM        = aws_ssm_parameter.config_jira_reporting_enabled.name
      JIRA_PROJECT_KEY                    = var.jira_project_key
      JIRA_ISSUE_TYPE                     = "Task"
      LOCAL_TIMEZONE                      = var.local_timezone
      JIRA_CONNECTOR_FUNCTION_NAME        = var.jira_connector_function_name
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-daily-reconciliation"
  })
}

resource "aws_lambda_function" "audit_log_ctl_forwarder" {
  filename         = data.archive_file.audit_log_ctl_forwarder.output_path
  function_name    = "${var.name_prefix}-log-ctl-forwarder"
  role             = aws_iam_role.lambda_role.arn
  handler          = "audit_log_ctl_forwarder.handler"
  runtime          = var.lambda_runtime
  timeout          = 300
  source_code_hash = data.archive_file.audit_log_ctl_forwarder.output_base64sha256

  environment {
    variables = {
      VAULT_LOG_GROUP      = var.vault_audit_loggroup_name
      POSTGRESQL_LOG_GROUP = var.rds_postgresql_loggroup_name
      CTL_CHANNEL_ARN      = var.cloudtrail_channel_arn
      DATABASE_FILTER      = var.database_audit_filter
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-log-ctl-forwarder"
  })
}

resource "aws_cloudwatch_log_group" "slack_access_request_handler" {
  name              = "/aws/lambda/${aws_lambda_function.slack_access_request_handler.function_name}"
  retention_in_days = var.slack_handler_log_retention_days

  tags = merge(var.tags, {
    Name = "/aws/lambda/${aws_lambda_function.slack_access_request_handler.function_name}"
  })
}

resource "aws_cloudwatch_log_group" "daily_reconciliation" {
  name              = "/aws/lambda/${aws_lambda_function.daily_reconciliation.function_name}"
  retention_in_days = var.reconciliation_log_retention_days

  tags = merge(var.tags, {
    Name = "/aws/lambda/${aws_lambda_function.daily_reconciliation.function_name}"
  })
}

resource "aws_cloudwatch_log_group" "audit_log_ctl_forwarder" {
  name              = "/aws/lambda/${aws_lambda_function.audit_log_ctl_forwarder.function_name}"
  retention_in_days = var.ctl_forwarder_log_retention_days

  tags = merge(var.tags, {
    Name = "/aws/lambda/${aws_lambda_function.audit_log_ctl_forwarder.function_name}"
  })
}

resource "aws_lambda_permission" "logs_invoke_audit_forwarder_vault" {
  statement_id  = "AllowCloudWatchLogsInvokeAuditForwarderVault"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.audit_log_ctl_forwarder.function_name
  principal     = "logs.${var.aws_region}.amazonaws.com"
  source_arn    = "arn:aws:logs:${var.aws_region}:${var.account_id}:log-group:${var.vault_audit_loggroup_name}:*"
}

resource "aws_cloudwatch_log_subscription_filter" "vault_creds" {
  name           = "${var.name_prefix}-vault-creds-filter"
  log_group_name = var.vault_audit_loggroup_name
  # Prod-only creds issuance
  filter_pattern  = "\"database\" \"creds\" \"prod-\""
  destination_arn = aws_lambda_function.audit_log_ctl_forwarder.arn

  depends_on = [aws_lambda_permission.logs_invoke_audit_forwarder_vault]
}
