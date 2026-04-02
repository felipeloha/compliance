resource "aws_ssm_parameter" "slack_signing_secret" {
  name        = "${local.ssm_prefix}/slack_signing_secret"
  description = "Slack signing secret (placeholder; update value manually in SSM after apply)"
  type        = "SecureString"
  value       = "CHANGE_ME"
  tags        = var.tags

  lifecycle {
    ignore_changes  = [value]
    prevent_destroy = true
  }
}

resource "aws_ssm_parameter" "config_allowed_durations" {
  name        = "${local.ssm_prefix}/allowed_durations"
  description = "Allowed durations (minutes) for temporary access; comma-separated"
  type        = "String"
  value       = join(",", tolist(var.allowed_durations))
  tags        = var.tags
}

resource "aws_ssm_parameter" "config_customer_data" {
  name        = "${local.ssm_prefix}/customer_data_config"
  description = "Customer data resources config as JSON"
  type        = "String"
  value       = var.customer_data_config
  tags        = var.tags
}

resource "aws_ssm_parameter" "slack_bot_token" {
  name        = "${local.ssm_prefix}/slack_bot_token"
  description = "Slack Bot OAuth token (placeholder; update value manually in SSM after apply)"
  type        = "SecureString"
  value       = "CHANGE_ME"
  tags        = var.tags

  lifecycle {
    ignore_changes  = [value]
    prevent_destroy = true
  }
}

# DB-specific whitelist: database service usernames
resource "aws_ssm_parameter" "config_whitelist_db_users" {
  name        = "${local.ssm_prefix}/whitelist_db_users"
  description = "JSON array of DB service usernames to whitelist from audit (e.g., ['nextcloud_v2','recommender_prod_user'])"
  type        = "String"
  value       = jsonencode(var.whitelist_db_users)
  tags        = var.tags
  lifecycle {
    ignore_changes  = [value]
    prevent_destroy = true
  }
}

# S3-specific whitelist: automated actors by category
resource "aws_ssm_parameter" "config_whitelist_s3_actors" {
  name        = "${local.ssm_prefix}/whitelist_s3_actors"
  description = "JSON object of S3 actors to whitelist by category (e.g., {'SERVICE_PRINCIPAL': ['s3-metadata-handler']})"
  type        = "String"
  value       = "{}"
  tags        = var.tags
  lifecycle {
    ignore_changes  = [value]
    prevent_destroy = true
  }
}

resource "aws_ssm_parameter" "config_jira_reporting_enabled" {
  name        = "${local.ssm_prefix}/jira_reporting_enabled"
  description = "Enable Jira ticket creation for violations (true/false)"
  type        = "String"
  value       = "false"
  lifecycle {
    ignore_changes  = [value]
    prevent_destroy = true
  }
  tags = var.tags
}
