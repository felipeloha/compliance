resource "aws_dynamodb_table" "access_requests" {
  name         = "${var.name_prefix}-requests"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "request_id"
  range_key    = "timestamp"

  attribute {
    name = "request_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "local_date"
    type = "S"
  }

  attribute {
    name = "user_email"
    type = "S"
  }

  attribute {
    name = "jira_issue_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  global_secondary_index {
    name            = "timestamp-index"
    hash_key        = "timestamp"
    range_key       = "request_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "user-email-index"
    hash_key        = "user_email"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "jira-issue-index"
    hash_key        = "jira_issue_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # GSI to efficiently query one local day (in configured LOCAL_TIMEZONE) and range by timestamp
  global_secondary_index {
    name            = "local-date-timestamp-index"
    hash_key        = "local_date"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-access-requests"
  })
}
