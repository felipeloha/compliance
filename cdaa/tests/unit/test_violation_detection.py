"""
Basic unit tests for Audit Customer Data Access module
"""

import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

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


class TestBasicFunctionality:
    """Basic test cases for the audit module"""

    def test_import_modules(self):
        """Test that all modules can be imported successfully"""
        # Test imports
        from audit_types import HumanViolationGroup, NonHumanViolations, ReportMetadata, Violation  # noqa: E401
        from config import Config  # noqa: E401
        from constants import JIRA_LABELS  # noqa: E401
        from services.jira_service import JiraService  # noqa: E401
        from services.violation_formatter import ViolationFormatter  # noqa: E401

        # If we get here, imports were successful
        assert True

    def test_constants(self):
        """Test that constants are properly defined"""
        from constants import JIRA_LABELS

        assert JIRA_LABELS == ["audit", "cdaa", "violation"]

    def test_audit_types(self):
        """Test that TypedDict definitions work"""
        from audit_types import HumanViolationGroup, NonHumanViolations, ReportMetadata, Violation

        # Test Violation
        violation = Violation(
            type="ACCESS_OUTSIDE_WINDOW",
            severity="MEDIUM",
            user_id="test@example.com",
            actor_type="HUMAN",
            resource_arn="arn:aws:s3:::test-bucket",
            event_time="2025-09-08 14:02:34.000",
            event_name="GetObject",
            description="Test violation",
            matched_request={"jira_issue_id": "SECO-123", "justification": "test"},
            resource_details={"s3_bucket": "test-bucket", "s3_key": "test-key"},
            evidence={"user_email": "test@example.com", "source_ip": "1.2.3.4"},
        )

        assert violation["type"] == "ACCESS_OUTSIDE_WINDOW"
        assert violation["severity"] == "MEDIUM"
        assert violation["user_id"] == "test@example.com"

    def test_config_initialization(self):
        """Test Config class initialization"""
        from config import Config

        config = Config()

        # Test environment variables are loaded
        assert config.jira_project_key == "PROJ"
        assert config.jira_issue_type == "Task"
        assert config.reconciliation_timezone == "Europe/Berlin"

    def test_jira_service_initialization(self):
        """Test JiraService initialization"""
        from config import Config
        from services.jira_service import JiraService

        config = Config()
        jira_service = JiraService(config)

        assert jira_service.config == config
        assert jira_service.formatter is not None

    def test_violation_formatter_initialization(self):
        """Test ViolationFormatter initialization"""
        from services.violation_formatter import ViolationFormatter

        formatter = ViolationFormatter()

        assert formatter is not None

    @patch("boto3.client")
    def test_daily_reconciliation_service_initialization(self, mock_boto3_client):
        """Test DailyReconciliationService initialization"""
        from daily_reconciliation import DailyReconciliationService

        # Mock the SSM client
        mock_ssm = MagicMock()
        mock_ssm.get_parameter.return_value = {"Parameter": {"Value": "test-value"}}
        mock_boto3_client.return_value = mock_ssm

        service = DailyReconciliationService()

        assert service is not None
        assert service.config is not None
        assert service.jira_service is not None

    def test_time_window_computation(self):
        """Test time window computation logic"""
        from daily_reconciliation import DailyReconciliationService

        service = DailyReconciliationService()

        # Test with a specific date range
        event = {"start": "2025-09-07T22:00:00Z", "end": "2025-09-08T21:59:59Z"}
        window_start, window_end = service._compute_time_window(event)

        # Should be previous day at 22:00 UTC to target day at 21:59:59 UTC
        assert window_start.year == 2025
        assert window_start.month == 9
        assert window_start.day == 7  # Previous day
        assert window_start.hour == 22
        assert window_start.minute == 0

        assert window_end.year == 2025
        assert window_end.month == 9
        assert window_end.day == 8  # Target day
        assert window_end.hour == 21
        assert window_end.minute == 59

    def test_violation_grouping(self):
        """Test violation grouping logic"""
        from daily_reconciliation import DailyReconciliationService

        service = DailyReconciliationService()

        violations = [
            {
                "type": "ACCESS_OUTSIDE_WINDOW",
                "user_id": "user1@example.com",
                "actor_type": "HUMAN",
                "severity": "MEDIUM",
            },
            {
                "type": "ACCESS_OUTSIDE_WINDOW",
                "user_id": "user1@example.com",
                "actor_type": "HUMAN",
                "severity": "HIGH",
            },
            {
                "type": "UNAUTHORIZED_ACCESS",
                "user_id": "service-account",
                "actor_type": "SERVICE",
                "severity": "CRITICAL",
            },
        ]

        human_groups, non_human_violations = service._group_violations(violations)

        assert len(human_groups) == 1
        assert human_groups[0]["user_email"] == "user1@example.com"
        assert human_groups[0]["violations_count"] == 2
        assert len(human_groups[0]["violations"]) == 2

        assert non_human_violations["total_count"] == 1
        assert len(non_human_violations["violations"]) == 1

    def test_actor_type_classification(self):
        """Test actor type classification"""
        from daily_reconciliation import DailyReconciliationService

        service = DailyReconciliationService()

        # Test human actor
        event = {"principalId": "user@example.com"}
        assert service._classify_actor_type(event, "user@example.com") == "HUMAN"

        # Test service actor
        event = {"principalId": "service-account", "sourceIpAddress": "s3.amazonaws.com"}
        assert service._classify_actor_type(event, None) == "AWS_SERVICE"

        # Test assumed role
        event = {"principalId": "AROARSCRHXIUXBUSAG5IN:user@example.com"}
        assert service._classify_actor_type(event, "user@example.com") == "HUMAN"

    def test_human_identifier_derivation(self):
        """Test human identifier derivation"""
        from daily_reconciliation import DailyReconciliationService

        service = DailyReconciliationService()

        # Test email extraction
        event = {"userIdentity": {"type": "IAMUser", "userName": "user@example.com"}}
        assert service._derive_human_identifier(event) == "user@example.com"

        # Test assumed role extraction
        event = {"userIdentity": {"type": "AssumedRole", "arn": "arn:aws:sts::123:assumed-role/Role/user@example.com"}}
        assert service._derive_human_identifier(event) == "user@example.com"

        # Test service account
        event = {"userIdentity": {"type": "Service", "userName": "service-account"}}
        assert service._derive_human_identifier(event) == "service-account"

    def test_resource_canonicalization(self):
        """Test resource canonicalization"""
        from daily_reconciliation import DailyReconciliationService

        service = DailyReconciliationService()

        # Test S3 resource
        event = {
            "eventName": "GetObject",
            "eventSource": "s3.amazonaws.com",
            "resourceArn": "arn:aws:s3:::test-bucket/test-key",
        }
        cfg = {"s3_buckets": ["arn:aws:s3:::test-bucket"]}
        canonical, details = service._canonicalize_resource(event, cfg)
        assert canonical == "arn:aws:s3:::test-bucket"

        # Test RDS resource
        event = {
            "eventName": "DbSessionConnect",
            "database": "test-db",
            "resourceArn": "arn:aws:rds:eu-central-1:123456789012:db:test-db",
        }
        cfg = {"rds_databases": ["arn:aws:rds:eu-central-1:123456789012:db:test-db"]}
        canonical, details = service._canonicalize_resource(event, cfg)
        assert canonical == "arn:aws:rds:eu-central-1:123456789012:db:test-db"

    def test_time_parsing(self):
        """Test time parsing to epoch seconds"""
        from daily_reconciliation import DailyReconciliationService

        service = DailyReconciliationService()

        time_str = "2025-09-08 14:02:34.000"
        epoch = service._parse_time_to_epoch_seconds(time_str)
        assert isinstance(epoch, (int, float))
        assert epoch > 0

    def test_violation_deduplication(self):
        """Test violation deduplication logic"""
        from daily_reconciliation import DailyReconciliationService

        service = DailyReconciliationService()

        violations = []
        seen_keys = set()

        violation1 = {
            "type": "ACCESS_OUTSIDE_WINDOW",
            "user_id": "user@example.com",
            "resource_arn": "arn:aws:s3:::test-bucket",
            "event_time": "2025-09-08 14:02:34.000",
        }

        violation2 = {
            "type": "ACCESS_OUTSIDE_WINDOW",
            "user_id": "user@example.com",
            "resource_arn": "arn:aws:s3:::test-bucket",
            "event_time": "2025-09-08 14:02:34.000",
        }

        # First violation should be added
        assert service._add_violation_if_new(violations, seen_keys, violation1) == True
        violations.append(violation1)  # Manually add since method only checks, doesn't add
        assert len(violations) == 1

        # Duplicate violation should not be added
        assert service._add_violation_if_new(violations, seen_keys, violation2) == False
        assert len(violations) == 1

    def test_s3_actor_skipping(self):
        """Test S3 actor skipping logic"""
        from daily_reconciliation import DailyReconciliationService

        service = DailyReconciliationService()

        # Test whitelisted service principal
        event = {"sessionIssuerUserName": "whitelisted-actor"}
        s3_actor_whitelist = {"SERVICE_PRINCIPAL": ["whitelisted-actor"]}
        assert service._should_skip_s3_actor(event, "SERVICE_PRINCIPAL", s3_actor_whitelist) == True

        # Test non-whitelisted service principal
        event = {"sessionIssuerUserName": "non-whitelisted-actor"}
        s3_actor_whitelist = {"SERVICE_PRINCIPAL": ["other-actor"]}
        assert service._should_skip_s3_actor(event, "SERVICE_PRINCIPAL", s3_actor_whitelist) == False


if __name__ == "__main__":
    pytest.main([__file__])
