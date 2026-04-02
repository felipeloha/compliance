#!/usr/bin/env python3
"""
Configuration management for Customer Data Access Audit (CDAA) system.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import boto3
from constants import DEFAULT_TIMEZONE

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for CDAA system."""

    def __init__(self):
        self._ssm_client = boto3.client("ssm")

    def _get_ssm_parameter(self, param_name: str, decrypt: bool = False) -> str:
        """Get SSM parameter value. Fail fast on any error."""
        try:
            response = self._ssm_client.get_parameter(Name=param_name, WithDecryption=decrypt)
            value = response["Parameter"]["Value"]

            if not value or value == "CHANGE_ME":
                raise ValueError(f"Parameter not configured in SSM: {param_name}")

            return value
        except Exception as e:
            logger.error(f"Failed to get parameter {param_name}: {e}")
            raise

    @property
    def dynamodb_table_name(self) -> str:
        """Get DynamoDB table name."""
        return os.environ["DYNAMODB_TABLE_NAME"]

    @property
    def cloudtrail_lake_event_data_store_id(self) -> str:
        """Get CloudTrail Lake Event Data Store ID."""
        return os.environ["CLOUDTRAIL_LAKE_EVENT_DATA_STORE_ID"]

    @property
    def cloudtrail_lake_curated_store_id(self) -> str:
        """Get CloudTrail Lake Curated Store ID."""
        return os.environ["CLOUDTRAIL_LAKE_CURATED_STORE_ID"]

    @property
    def customer_data_config_param(self) -> str:
        """Get customer data config parameter name."""
        return os.environ["CUSTOMER_DATA_CONFIG_PARAM"]

    @property
    def jira_project_key(self) -> str:
        """Get Jira project key."""
        value = os.environ.get("JIRA_PROJECT_KEY")
        if value is None:
            raise ValueError("JIRA_PROJECT_KEY environment variable is required")
        return value

    @property
    def jira_issue_type(self) -> str:
        """Get Jira issue type."""
        value = os.environ.get("JIRA_ISSUE_TYPE")
        if value is None:
            raise ValueError("JIRA_ISSUE_TYPE environment variable is required")
        return value

    @property
    def reconciliation_timezone(self) -> str:
        """Get reconciliation timezone."""
        return os.environ.get("LOCAL_TIMEZONE", DEFAULT_TIMEZONE)

    @property
    def jira_reporting_enabled(self) -> bool:
        """Check if Jira reporting is enabled."""
        param_name = os.environ["JIRA_REPORTING_ENABLED_PARAM"]
        value = self._get_ssm_parameter(param_name, decrypt=False)

        if value.lower() in ("true", "1", "yes", "on"):
            return True
        elif value.lower() in ("false", "0", "no", "off"):
            return False
        else:
            raise ValueError(f"Invalid boolean value for Jira reporting enabled: {value}")

    def get_customer_data_config(self) -> Dict[str, Any]:
        """Load customer data configuration from SSM."""
        try:
            param_name = self.customer_data_config_param
            value = self._get_ssm_parameter(param_name, decrypt=False)
            return json.loads(value)
        except Exception as e:
            logger.error(f"Failed to load customer data config: {e}")
            raise

    def get_whitelist_s3_actors(self) -> Dict[str, List[str]]:
        """Load whitelisted S3 actors from SSM."""
        param_name = os.environ.get("WHITELIST_S3_ACTORS_PARAM")
        if not param_name:
            raise ValueError("WHITELIST_S3_ACTORS_PARAM environment variable not set")

        value = self._get_ssm_parameter(param_name, decrypt=False)
        parsed_object = json.loads(value)

        if not isinstance(parsed_object, dict):
            raise ValueError("S3 actors whitelist must be a dictionary")

        result = {}
        for actor_type, patterns in parsed_object.items():
            if isinstance(patterns, list):
                result[str(actor_type)] = [str(p).strip().lower() for p in patterns]
        return result

    def get_whitelist_db_users(self) -> List[str]:
        """Load whitelisted database users from SSM."""
        param_name = os.environ.get("WHITELIST_DB_USERS_PARAM")
        if not param_name:
            raise ValueError("WHITELIST_DB_USERS_PARAM environment variable not set")

        value = self._get_ssm_parameter(param_name, decrypt=False)
        parsed_array = json.loads(value)

        if not isinstance(parsed_array, list):
            raise ValueError("DB users whitelist must be a list")

        return [str(username).strip().lower() for username in parsed_array]
