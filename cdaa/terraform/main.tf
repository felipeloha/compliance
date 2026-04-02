terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws     = { source = "hashicorp/aws", version = ">= 5.0" }
    archive = { source = "hashicorp/archive", version = ">= 2.4" }
  }
}

locals {
  name_prefix = var.name_prefix
  tags        = var.tags
  account_id  = var.account_id
  region      = var.aws_region
  ssm_prefix  = coalesce(var.ssm_param_prefix, "/audit/${var.name_prefix}")
}
