data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    sid     = "LambdaAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "${var.name_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "lambda_permissions" {
  statement {
    sid    = "SSMParameterAccess"
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters"
    ]
    resources = [
      aws_ssm_parameter.slack_signing_secret.arn,
      aws_ssm_parameter.slack_bot_token.arn,
      aws_ssm_parameter.config_allowed_durations.arn,
      aws_ssm_parameter.config_customer_data.arn,
      aws_ssm_parameter.config_whitelist_db_users.arn,
      aws_ssm_parameter.config_whitelist_s3_actors.arn,
      aws_ssm_parameter.config_jira_reporting_enabled.arn
    ]
  }

  statement {
    sid    = "DynamoDBAccess"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:UpdateItem"
    ]
    resources = [
      aws_dynamodb_table.access_requests.arn,
      "${aws_dynamodb_table.access_requests.arn}/index/*"
    ]
  }

  statement {
    sid    = "CloudTrailLakeQuery"
    effect = "Allow"
    actions = [
      "cloudtrail:StartQuery",
      "cloudtrail:GetQueryResults"
    ]
    resources = [
      aws_cloudtrail_event_data_store.customer_data_access_audit_events.arn,
      awscc_cloudtrail_event_data_store.customer_data_access_curated_events.event_data_store_arn
    ]
  }

  statement {
    sid    = "CloudTrailDataPutAuditEvents"
    effect = "Allow"
    actions = [
      "cloudtrail-data:PutAuditEvents"
    ]
    resources = [awscc_cloudtrail_channel.audit_customer_data_access_channel.id]
  }

  # EventBridge put to default bus
  statement {
    sid    = "EventBridgePutEvents"
    effect = "Allow"
    actions = [
      "events:PutEvents"
    ]
    resources = [data.aws_cloudwatch_event_bus.default.arn]
  }

  # Lambda invoke permission for Jira connector
  statement {
    sid    = "LambdaInvokeJiraConnector"
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction"
    ]
    resources = [
      "arn:aws:lambda:${var.aws_region}:${var.account_id}:function:${var.jira_connector_function_name}"
    ]
  }

  # IAM user tag access for email correlation
  statement {
    sid    = "IAMUserTagAccess"
    effect = "Allow"
    actions = [
      "iam:ListUserTags"
    ]
    resources = [
      "arn:aws:iam::${var.account_id}:user/*"
    ]
  }
}

resource "aws_iam_role_policy" "lambda_permissions" {
  name   = "${var.name_prefix}-lambda-permissions"
  role   = aws_iam_role.lambda_role.id
  policy = data.aws_iam_policy_document.lambda_permissions.json
}
