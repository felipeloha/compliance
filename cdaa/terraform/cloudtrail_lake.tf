resource "aws_cloudtrail_event_data_store" "customer_data_access_audit_events" {
  name                           = "${local.name_prefix}-events"
  multi_region_enabled           = true
  organization_enabled           = false
  retention_period               = var.cloudtrail_lake_retention_period_days
  billing_mode                   = var.cloudtrail_lake_billing_mode
  termination_protection_enabled = true

  # Data events – selectors for S3 etc. (native Lake ingestion)
  dynamic "advanced_event_selector" {
    for_each = contains(var.cloudtrail_lake_event_categories, "Data") ? var.cloudtrail_lake_data_event_resource_types : []
    content {
      name = "Data-${advanced_event_selector.value}"
      field_selector {
        field  = "eventCategory"
        equals = ["Data"]
      }
      field_selector {
        field  = "resources.type"
        equals = [advanced_event_selector.value]
      }
      dynamic "field_selector" {
        for_each = advanced_event_selector.value == "AWS::S3::Object" && length(var.cloudtrail_lake_s3_object_arns_prefixes) > 0 ? [1] : []
        content {
          field       = "resources.ARN"
          starts_with = var.cloudtrail_lake_s3_object_arns_prefixes
        }
      }
      dynamic "field_selector" {
        for_each = advanced_event_selector.value == "AWS::S3::Object" && length(var.cloudtrail_lake_s3_object_event_names) > 0 ? [1] : []
        content {
          field  = "eventName"
          equals = var.cloudtrail_lake_s3_object_event_names
        }
      }
    }
  }

  tags = local.tags
}

# Curated events EDS for Channel (must be ActivityAuditLog only)
resource "awscc_cloudtrail_event_data_store" "customer_data_access_curated_events" {
  name                           = "${local.name_prefix}-curated"
  multi_region_enabled           = false
  organization_enabled           = false
  retention_period               = var.cloudtrail_lake_retention_period_days
  billing_mode                   = var.cloudtrail_lake_billing_mode
  termination_protection_enabled = true
  ingestion_enabled              = true

  advanced_event_selectors = [{
    field_selectors = [{
      field  = "eventCategory"
      equals = ["ActivityAuditLog"]
    }]
  }]

  tags = [for k, v in local.tags : { key = k, value = v }]
}

resource "awscc_cloudtrail_channel" "audit_customer_data_access_channel" {
  name   = "${local.name_prefix}-channel"
  source = "Custom"

  destinations = [
    {
      type     = "EVENT_DATA_STORE"
      location = awscc_cloudtrail_event_data_store.customer_data_access_curated_events.event_data_store_arn
    }
  ]

  tags = [for k, v in local.tags : { key = k, value = v }]
}
