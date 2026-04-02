output "lambda_function_name_slack_handler" {
  description = "Name of the Slack access request handler Lambda function"
  value       = aws_lambda_function.slack_access_request_handler.function_name
}

output "lambda_function_name_daily_reconciliation" {
  description = "Name of the daily reconciliation Lambda function"
  value       = aws_lambda_function.daily_reconciliation.function_name
}

output "lambda_function_arns" {
  description = "ARNs of all Lambda functions"
  value = {
    slack_access_request_handler = aws_lambda_function.slack_access_request_handler.arn
    daily_reconciliation         = aws_lambda_function.daily_reconciliation.arn
    audit_log_ctl_forwarder      = aws_lambda_function.audit_log_ctl_forwarder.arn
  }
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table for access requests"
  value       = aws_dynamodb_table.access_requests.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table for access requests"
  value       = aws_dynamodb_table.access_requests.arn
}

output "cloudtrail_lake_event_data_store_id" {
  description = "ID of the CloudTrail Lake event data store"
  value       = aws_cloudtrail_event_data_store.customer_data_access_audit_events.id
}

output "cloudtrail_lake_event_data_store_arn" {
  description = "ARN of the CloudTrail Lake event data store"
  value       = aws_cloudtrail_event_data_store.customer_data_access_audit_events.arn
}

output "api_gateway_url_slack" {
  description = "URL of the API Gateway endpoint"
  value       = "${aws_apigatewayv2_api.slack_api.api_endpoint}${var.api_path}"
}

output "api_gateway_http_api_id" {
  description = "HTTP API ID of the Slack API Gateway"
  value       = aws_apigatewayv2_api.slack_api.id
}

output "api_gateway_slack_execution_arn" {
  description = "Execution ARN of the API Gateway (Slack)"
  value       = aws_apigatewayv2_api.slack_api.execution_arn
}

output "ssm_param_paths" {
  description = "Map of SSM parameter paths used by the module"
  value = {
    slack_signing_secret   = aws_ssm_parameter.slack_signing_secret.name
    allowed_durations      = aws_ssm_parameter.config_allowed_durations.name
    customer_data_config   = aws_ssm_parameter.config_customer_data.name
    slack_bot_token        = aws_ssm_parameter.slack_bot_token.name
    whitelist_db_users     = aws_ssm_parameter.config_whitelist_db_users.name
    whitelist_s3_actors    = aws_ssm_parameter.config_whitelist_s3_actors.name
    jira_reporting_enabled = aws_ssm_parameter.config_jira_reporting_enabled.name
  }
}

output "lambda_function_name_audit_log_ctl_forwarder" {
  description = "Name of the audit log forwarder Lambda function"
  value       = aws_lambda_function.audit_log_ctl_forwarder.function_name
}
