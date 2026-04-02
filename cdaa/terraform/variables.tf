variable "name_prefix" {
  description = "Prefix used for naming resources"
  type        = string
}
variable "account_id" {
  description = "AWS account ID to use for ARNs and defaults"
  type        = string
}

variable "ssm_param_prefix" {
  description = "Base prefix for SSM parameters (e.g. /audit/audit-customer-data-access). Default: /audit/<name_prefix>/"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "dynamodb_table_name" {
  description = "Optional DynamoDB table name for access requests; if null, module creates one"
  type        = string
  default     = null
}

variable "allowed_durations" {
  description = "List of allowed access durations in minutes"
  type        = list(number)
  default     = [15, 30, 60]
}

variable "api_path" {
  description = "API Gateway route path for Slack commands (e.g., /slack/commands)"
  type        = string
  default     = "/slack/commands"
}

variable "cloudtrail_lake_retention_period_days" {
  description = "Retention period for CloudTrail Lake event data store in days. Default: 1 year (365 days). For C5 compliance, override to 2555 days (7 years)."
  type        = number
  default     = 365
  validation {
    condition     = var.cloudtrail_lake_retention_period_days >= 7 && var.cloudtrail_lake_retention_period_days <= 2555
    error_message = "Retention period must be between 7 and 2555 days (CloudTrail Lake limits)."
  }
}

variable "cloudtrail_lake_billing_mode" {
  description = "CloudTrail Lake billing mode. Use EXTENDABLE_RETENTION_PRICING (default) for 1-year retention included with option to extend later; use FIXED_RETENTION_PRICING for fixed 7-year retention included. Note: FIXED maps to the console's 'Seven-year retention pricing'."
  type        = string
  default     = "EXTENDABLE_RETENTION_PRICING"
}

variable "cloudtrail_lake_event_categories" {
  description = "CloudTrail event categories to ingest. If including 'Data', CloudTrail Lake requires also specifying 'resources.type' (see var.cloudtrail_lake_data_event_resource_types)."
  type        = list(string)
  default     = ["Management", "Data"]
}

variable "cloudtrail_lake_data_event_resource_types" {
  description = "List of CloudTrail Lake data event resource types to include when eventCategories contains 'Data'. Common values: AWS::S3::Object, AWS::DynamoDB::Table, AWS::Lambda::Function"
  type        = list(string)
  default = [
    "AWS::S3::Object"
  ]
}

variable "cloudtrail_lake_s3_object_arns_prefixes" {
  description = "Optional list of S3 ARN prefixes to scope data events for AWS::S3::Object (e.g., ['arn:aws:s3:::***REMOVED***-daiswas/']). WARNING: If left empty, CloudTrail Lake may ingest S3 object events for all resources matching the type, which can cause very high costs."
  type        = list(string)
  default     = []
}

variable "cloudtrail_lake_s3_object_event_names" {
  description = "Optional list of S3 object-level event names to include (e.g., ['GetObject','PutObject','DeleteObject']). WARNING: Broad event selection increases volume and cost; if unset, no eventName filter is applied."
  type        = list(string)
  default     = []
}

variable "audit_report_format" {
  description = "Format for audit reports (json, csv, xml)"
  type        = string
  default     = "json"
  validation {
    condition     = contains(["json", "csv", "xml"], var.audit_report_format)
    error_message = "Audit report format must be one of: json, csv, xml."
  }
}

variable "customer_data_config" {
  description = "JSON string for customer data resources {\"s3_buckets\":[...],\"rds_databases\":[...]}"
  type        = string
  default     = null
}

variable "customer_data_resources" {
  description = "JSON string enumerating customer data resources to reconcile. Mirrors customer_data_config. Example: {\"rds_databases\":[\"arn:aws:rds:eu-central-1:ACCOUNT_ID:db:***REMOVED***-prod\"],\"s3_buckets\":[\"arn:aws:s3:::customer-prod-bucket\"]}"
  type        = string
  default     = "{}"
}

variable "lambda_runtime" {
  description = "Python runtime for Lambda functions"
  type        = string
  default     = "python3.13"
}

variable "daily_reconciliation_cron" {
  description = "Cron expression for daily reconciliation. Default: 03:00 UTC to process previous day's data."
  type        = string
  default     = "cron(0 3 * * ? *)"
}

variable "slack_lambda_timeout" {
  description = "Timeout (seconds) for Slack access request handler Lambda"
  type        = number
  default     = 30
}

variable "slack_lambda_memory_mb" {
  description = "Memory size (MB) for Slack access request handler Lambda"
  type        = number
  default     = 128
}

variable "reconciliation_lambda_timeout" {
  description = "Timeout (seconds) for daily reconciliation Lambda"
  type        = number
  default     = 900
}

variable "reconciliation_lambda_memory_mb" {
  description = "Memory size (MB) for daily reconciliation Lambda"
  type        = number
  default     = 512
}

variable "rds_postgresql_loggroup_name" {
  description = "CloudWatch log group name for PostgreSQL logs"
  type        = string
}

variable "vault_audit_loggroup_name" {
  description = "CloudWatch log group name for Vault audit logs"
  type        = string
}

variable "database_audit_filter" {
  description = "Comma-separated list of database names to audit (e.g., 'recommender_prod,nextcloud_v2')"
  type        = string
  default     = ""
}

variable "cw_metric_alarm_actions" {
  description = "List of SNS topic ARNs for CloudWatch metric alarm actions (e.g., Slack notifications)"
  type        = list(string)
  default     = []
}

variable "access_request_retention_years" {
  description = "Retention period for access request records in years (compliance requirement: minimum 1 year)"
  type        = number
  default     = 1
  validation {
    condition     = var.access_request_retention_years >= 1
    error_message = "Access request retention must be at least 1 year for compliance requirements."
  }
}

variable "local_timezone" {
  description = "Local timezone for date calculations and reconciliation windows (e.g., 'Europe/Berlin', 'America/New_York')"
  type        = string
  default     = "Europe/Berlin"
}

variable "jira_connector_function_name" {
  description = "Name of the Jira connector Lambda function for creating tickets"
  type        = string
  default     = null
}

variable "aws_region" {
  description = "AWS region for the provider"
  type        = string
  default     = "eu-central-1"
}

variable "jira_project_key" {
  description = "Jira project key for creating violation tickets"
  type        = string
}

variable "slack_handler_log_retention_days" {
  description = "CloudWatch log retention period in days for Slack access request handler Lambda function"
  type        = number
  default     = 30
  validation {
    condition     = var.slack_handler_log_retention_days >= 1 && var.slack_handler_log_retention_days <= 3653
    error_message = "Slack handler log retention must be between 1 and 3653 days."
  }
}

variable "reconciliation_log_retention_days" {
  description = "CloudWatch log retention period in days for daily reconciliation Lambda function"
  type        = number
  default     = 30
  validation {
    condition     = var.reconciliation_log_retention_days >= 1 && var.reconciliation_log_retention_days <= 3653
    error_message = "Reconciliation log retention must be between 1 and 3653 days."
  }
}

variable "ctl_forwarder_log_retention_days" {
  description = "CloudWatch log retention period in days for audit log CTL forwarder Lambda function"
  type        = number
  default     = 30
  validation {
    condition     = var.ctl_forwarder_log_retention_days >= 1 && var.ctl_forwarder_log_retention_days <= 3653
    error_message = "CTL forwarder log retention must be between 1 and 3653 days."
  }
}

variable "whitelist_db_users" {
  description = "List of database users to whitelist from audit"
  type        = list(string)
  default     = []
}

variable "cloudtrail_lake_event_data_store_id" {
  description = "CloudTrail Lake native event data store ID. For localstack, set to any non-empty string."
  type        = string
  default     = null
}

variable "cloudtrail_lake_curated_store_id" {
  description = "CloudTrail Lake curated event data store ID. For localstack, set to any non-empty string."
  type        = string
  default     = null
}

variable "cloudtrail_channel_arn" {
  description = "CloudTrail channel ARN for the CTL forwarder Lambda. For localstack, set to any non-empty string."
  type        = string
  default     = null
}
