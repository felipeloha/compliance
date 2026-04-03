"""
Unit tests for Configuration module
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

# Mock environment variables
os.environ["DYNAMODB_TABLE_NAME"] = "test-table"
os.environ["CLOUDTRAIL_LAKE_EVENT_DATA_STORE_ID"] = "test-event-store"
os.environ["CLOUDTRAIL_LAKE_CURATED_STORE_ID"] = "test-curated-store"
os.environ["CUSTOMER_DATA_CONFIG_PARAM"] = "/test/customer_data_config"
os.environ["WHITELIST_DB_USERS_PARAM"] = "/test/whitelist_db_users"
os.environ["WHITELIST_S3_ACTORS_PARAM"] = "/test/whitelist_s3_actors"
os.environ["JIRA_PROJECT_KEY"] = "PROJ"
os.environ["JIRA_ISSUE_TYPE"] = "Task"
os.environ["LOCAL_TIMEZONE"] = "Europe/Berlin"
os.environ["JIRA_REPORTING_ENABLED_PARAM"] = "/test/jira_reporting_enabled"
os.environ["JIRA_CONNECTOR_FUNCTION_NAME"] = "test-jira-connector"

import sys

# Patch boto3 client and resource before importing the module to avoid real AWS calls at import-time
_boto3_client_patcher = patch("boto3.client", side_effect=lambda svc: MagicMock())
_boto3_client_patcher.start()

_boto3_resource_patcher = patch("boto3.resource", side_effect=lambda svc: MagicMock())
_boto3_resource_patcher.start()

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "terraform", "lambda"))
from config import Config  # noqa: E402


class TestConfig:
    """Test cases for Configuration class"""

    @pytest.fixture
    def mock_ssm_client(self):
        """Mock SSM client"""
        with patch("boto3.client") as mock_boto3:
            mock_ssm = MagicMock()
            mock_boto3.return_value = mock_ssm

            def mock_get_parameter(Name, WithDecryption=False):
                if "slack_signing_secret" in Name:
                    return {"Parameter": {"Value": "test-signing-secret"}}
                elif "customer_data_config" in Name:
                    return {
                        "Parameter": {
                            "Value": json.dumps(
                                {
                                    "s3_buckets": ["test-bucket-1", "test-bucket-2"],
                                    "rds_instances": ["test-rds-1", "test-rds-2"],
                                    "allowed_durations": [15, 30, 60, 120],
                                }
                            )
                        }
                    }
                elif "whitelist_db_users" in Name:
                    return {"Parameter": {"Value": json.dumps(["user1", "user2", "user3"])}}
                elif "whitelist_s3_actors" in Name:
                    return {"Parameter": {"Value": json.dumps({"HUMAN": ["actor1", "actor2", "actor3"]})}}
                elif "jira_reporting_enabled" in Name:
                    return {"Parameter": {"Value": "true"}}
                else:
                    return {"Parameter": {"Value": "test-value"}}

            mock_ssm.get_parameter.side_effect = mock_get_parameter
            yield mock_ssm

    def test_config_initialization(self, mock_ssm_client):
        """Test configuration initialization"""
        config = Config()

        # Test environment variables
        assert config.dynamodb_table_name == "test-table"
        assert config.cloudtrail_lake_event_data_store_id == "test-event-store"
        assert config.cloudtrail_lake_curated_store_id == "test-curated-store"
        assert config.customer_data_config_param == "/test/customer_data_config"
        assert config.jira_project_key == "PROJ"
        assert config.jira_issue_type == "Task"
        assert config.reconciliation_timezone == "Europe/Berlin"

    def test_load_customer_data_config(self, mock_ssm_client):
        """Test customer data configuration loading"""
        config = Config()
        customer_data_config = config.get_customer_data_config()

        assert customer_data_config["s3_buckets"] == ["test-bucket-1", "test-bucket-2"]
        assert customer_data_config["rds_instances"] == ["test-rds-1", "test-rds-2"]
        assert customer_data_config["allowed_durations"] == [15, 30, 60, 120]

    def test_load_whitelist_db_users(self, mock_ssm_client):
        """Test whitelist DB users loading"""
        config = Config()
        whitelist = config.get_whitelist_db_users()

        assert whitelist == ["user1", "user2", "user3"]

    def test_load_whitelist_s3_actors(self, mock_ssm_client):
        """Test whitelist S3 actors loading"""
        config = Config()
        whitelist = config.get_whitelist_s3_actors()

        assert whitelist == {"HUMAN": ["actor1", "actor2", "actor3"]}

    def test_load_jira_reporting_enabled(self, mock_ssm_client):
        """Test Jira reporting enabled loading"""
        config = Config()
        enabled = config.jira_reporting_enabled

        assert enabled is True

    def test_load_jira_reporting_enabled_false(self, mock_ssm_client):
        """Test Jira reporting enabled loading when false"""

        def mock_get_parameter(Name, WithDecryption=False):
            if "jira_reporting_enabled" in Name:
                return {"Parameter": {"Value": "false"}}
            else:
                return {"Parameter": {"Value": "test-value"}}

        mock_ssm_client.get_parameter.side_effect = mock_get_parameter

        config = Config()
        enabled = config.jira_reporting_enabled

        assert enabled is False

    def test_load_customer_data_config_invalid_json(self, mock_ssm_client):
        """Test customer data configuration loading with invalid JSON"""

        def mock_get_parameter(Name, WithDecryption=False):
            if "customer_data_config" in Name:
                return {"Parameter": {"Value": "invalid-json"}}
            else:
                return {"Parameter": {"Value": "test-value"}}

        mock_ssm_client.get_parameter.side_effect = mock_get_parameter

        config = Config()

        # Config raises exception for invalid JSON
        with pytest.raises(json.JSONDecodeError):
            config.get_customer_data_config()

    def test_load_whitelist_db_users_invalid_json(self, mock_ssm_client):
        """Test whitelist DB users loading with invalid JSON"""

        def mock_get_parameter(Name, WithDecryption=False):
            if "whitelist_db_users" in Name:
                return {"Parameter": {"Value": "invalid-json"}}
            else:
                return {"Parameter": {"Value": "test-value"}}

        mock_ssm_client.get_parameter.side_effect = mock_get_parameter

        config = Config()

        # Config raises exception for invalid JSON
        with pytest.raises(json.JSONDecodeError):
            config.get_whitelist_db_users()

    def test_load_whitelist_s3_actors_invalid_json(self, mock_ssm_client):
        """Test whitelist S3 actors loading with invalid JSON"""

        def mock_get_parameter(Name, WithDecryption=False):
            if "whitelist_s3_actors" in Name:
                return {"Parameter": {"Value": "invalid-json"}}
            else:
                return {"Parameter": {"Value": "test-value"}}

        mock_ssm_client.get_parameter.side_effect = mock_get_parameter

        config = Config()

        # Config raises exception for invalid JSON
        with pytest.raises(json.JSONDecodeError):
            config.get_whitelist_s3_actors()

    def test_load_jira_reporting_enabled_invalid_value(self, mock_ssm_client):
        """Test Jira reporting enabled loading with invalid value"""

        def mock_get_parameter(Name, WithDecryption=False):
            if "jira_reporting_enabled" in Name:
                return {"Parameter": {"Value": "invalid-boolean"}}
            else:
                return {"Parameter": {"Value": "test-value"}}

        mock_ssm_client.get_parameter.side_effect = mock_get_parameter

        config = Config()

        # Config raises exception for invalid boolean
        with pytest.raises(ValueError):
            config.jira_reporting_enabled

    def test_load_customer_data_config_ssm_error(self, mock_ssm_client):
        """Test customer data configuration loading with SSM error"""
        mock_ssm_client.get_parameter.side_effect = Exception("SSM error")

        config = Config()

        # Config raises exception for SSM error
        with pytest.raises(Exception, match="SSM error"):
            config.get_customer_data_config()

    def test_load_whitelist_db_users_ssm_error(self, mock_ssm_client):
        """Test whitelist DB users loading with SSM error"""
        mock_ssm_client.get_parameter.side_effect = Exception("SSM error")

        config = Config()

        # Config raises exception for SSM error
        with pytest.raises(Exception, match="SSM error"):
            config.get_whitelist_db_users()

    def test_load_whitelist_s3_actors_ssm_error(self, mock_ssm_client):
        """Test whitelist S3 actors loading with SSM error"""
        mock_ssm_client.get_parameter.side_effect = Exception("SSM error")

        config = Config()

        # Config raises exception for SSM error
        with pytest.raises(Exception, match="SSM error"):
            config.get_whitelist_s3_actors()

    def test_load_jira_reporting_enabled_ssm_error(self, mock_ssm_client):
        """Test Jira reporting enabled loading with SSM error"""
        mock_ssm_client.get_parameter.side_effect = Exception("SSM error")

        config = Config()

        # Config raises exception for SSM error
        with pytest.raises(Exception, match="SSM error"):
            config.jira_reporting_enabled

    def test_missing_environment_variables(self):
        """Test configuration with missing environment variables"""
        env_vars_to_clear = [
            "DYNAMODB_TABLE_NAME",
            "CLOUDTRAIL_LAKE_EVENT_DATA_STORE_ID",
            "CLOUDTRAIL_LAKE_CURATED_STORE_ID",
            "CUSTOMER_DATA_CONFIG_PARAM",
            "WHITELIST_DB_USERS_PARAM",
            "WHITELIST_S3_ACTORS_PARAM",
            "JIRA_PROJECT_KEY",
            "JIRA_ISSUE_TYPE",
            "LOCAL_TIMEZONE",
            "JIRA_REPORTING_ENABLED_PARAM",
            "JIRA_CONNECTOR_FUNCTION_NAME",
        ]

        saved = {var: os.environ.pop(var) for var in env_vars_to_clear if var in os.environ}
        try:
            config = Config()
            assert config is not None
        finally:
            os.environ.update(saved)

    def test_reconciliation_timezone_property(self, mock_ssm_client):
        """Test reconciliation timezone property"""
        config = Config()

        assert config.reconciliation_timezone == "Europe/Berlin"

    def test_jira_reporting_enabled_property(self, mock_ssm_client):
        """Test Jira reporting enabled property"""
        # Ensure environment variable is set
        os.environ["JIRA_REPORTING_ENABLED_PARAM"] = "/test/jira_reporting_enabled"
        config = Config()

        assert config.jira_reporting_enabled is True

    def test_customer_data_config_property(self, mock_ssm_client):
        """Test customer data config property"""
        # Ensure environment variable is set
        os.environ["CUSTOMER_DATA_CONFIG_PARAM"] = "/test/customer_data_config"
        config = Config()
        customer_data_config = config.get_customer_data_config()

        assert customer_data_config["s3_buckets"] == ["test-bucket-1", "test-bucket-2"]
        assert customer_data_config["rds_instances"] == ["test-rds-1", "test-rds-2"]
        assert customer_data_config["allowed_durations"] == [15, 30, 60, 120]

    def test_whitelist_db_users_property(self, mock_ssm_client):
        """Test whitelist DB users property"""
        # Ensure environment variable is set
        os.environ["WHITELIST_DB_USERS_PARAM"] = "/test/whitelist_db_users"
        config = Config()
        whitelist = config.get_whitelist_db_users()

        assert whitelist == ["user1", "user2", "user3"]

    def test_whitelist_s3_actors_property(self, mock_ssm_client):
        """Test whitelist S3 actors property"""
        # Ensure environment variable is set
        os.environ["WHITELIST_S3_ACTORS_PARAM"] = "/test/whitelist_s3_actors"
        config = Config()
        whitelist = config.get_whitelist_s3_actors()

        assert whitelist == {"HUMAN": ["actor1", "actor2", "actor3"]}


if __name__ == "__main__":
    pytest.main([__file__])
