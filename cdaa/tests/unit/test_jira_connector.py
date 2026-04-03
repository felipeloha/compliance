"""
Unit tests for Service classes
"""

import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mock environment variables
os.environ["JIRA_PROJECT_KEY"] = "PROJ"
os.environ["JIRA_ISSUE_TYPE"] = "Task"
os.environ["JIRA_CONNECTOR_FUNCTION_NAME"] = "test-jira-connector"

import sys

# Patch boto3 client and resource before importing the module to avoid real AWS calls at import-time
_boto3_client_patcher = patch("boto3.client", side_effect=lambda svc: MagicMock())
_boto3_client_patcher.start()

_boto3_resource_patcher = patch("boto3.resource", side_effect=lambda svc: MagicMock())
_boto3_resource_patcher.start()

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "terraform", "lambda"))
from audit_types import HumanViolationGroup, NonHumanViolations, ReportMetadata, Violation  # noqa: E402
from services.jira_service import JiraService  # noqa: E402
from services.violation_formatter import ViolationFormatter  # noqa: E402


class TestJiraService:
    """Test cases for Jira Service"""

    @pytest.fixture
    def jira_service(self):
        """Create JiraService instance"""
        from config import Config

        config = Config()
        return JiraService(config)

    @patch("config.boto3.client")
    def test_create_human_violation_ticket(self, mock_boto3_client):
        """Test human violation ticket creation"""
        # Set required environment variables
        os.environ["JIRA_REPORTING_ENABLED_PARAM"] = "/test/jira-reporting-enabled"
        os.environ["JIRA_CONNECTOR_FUNCTION_NAME"] = "test-jira-connector"
        os.environ["JIRA_PROJECT_KEY"] = "PROJ"
        os.environ["JIRA_ISSUE_TYPE"] = "Task"

        # Mock SSM client
        mock_ssm_client = mock_boto3_client.return_value
        mock_ssm_client.get_parameter.return_value = {"Parameter": {"Value": "true"}}

        # Create JiraService after mocking
        from config import Config
        from services.jira_service import JiraService

        config = Config()
        jira_service = JiraService(config)

        # Mock successful Lambda invocation
        mock_lambda_client = Mock()
        mock_lambda_client.invoke.return_value = {"StatusCode": 200, "Payload": Mock()}
        mock_lambda_client.invoke.return_value["Payload"].read.return_value = json.dumps(
            {"statusCode": 200, "body": json.dumps({"success": True, "issue_key": "SECO-123"})}
        )
        jira_service.lambda_client = mock_lambda_client

        user_group = HumanViolationGroup(
            user_email="test@example.com",
            violations_count=2,
            violations=[
                {
                    "type": "ACCESS_OUTSIDE_WINDOW",
                    "severity": "MEDIUM",
                    "user_id": "test@example.com",
                    "actor_type": "HUMAN",
                    "resource_arn": "arn:aws:s3:::test-bucket",
                    "event_time": "2025-09-08 14:02:34.000",
                    "event_name": "GetObject",
                    "description": "Test violation",
                    "matched_request": {"jira_issue_id": "SECO-0000", "justification": "test"},
                    "resource_details": {"s3_bucket": "test-bucket", "s3_key": "test-key"},
                    "evidence": {"user_email": "test@example.com", "source_ip": "1.2.3.4"},
                }
            ],
        )

        report_metadata = ReportMetadata(generated_at="2025-09-08T10:00:00Z", execution_duration_seconds=30.5)

        time_period = {
            "start": "2025-09-07T22:00:00Z",
            "end": "2025-09-08T21:59:59Z",
            "start_local": "2025-09-08T00:00:00+02:00",
            "end_local": "2025-09-08T23:59:59+02:00",
        }

        result = jira_service.create_human_violation_ticket(user_group, report_metadata, time_period)

        assert result == "SECO-123"
        mock_lambda_client.invoke.assert_called_once()

        # Verify the payload structure
        call_args = mock_lambda_client.invoke.call_args
        payload = json.loads(call_args[1]["Payload"])

        assert payload["project_key"] == "PROJ"
        assert payload["issue_type"] == "Task"
        assert "audit" in payload["labels"]
        assert "cdaa" in payload["labels"]
        assert "violation" in payload["labels"]
        assert "test@example.com" in payload["summary"]
        assert "test@example.com" in payload["description"]

    @patch("config.boto3.client")
    def test_create_non_human_violation_ticket(self, mock_boto3_client):
        """Test non-human violation ticket creation"""
        # Set required environment variables
        os.environ["JIRA_REPORTING_ENABLED_PARAM"] = "/test/jira-reporting-enabled"
        os.environ["JIRA_CONNECTOR_FUNCTION_NAME"] = "test-jira-connector"
        os.environ["JIRA_PROJECT_KEY"] = "PROJ"
        os.environ["JIRA_ISSUE_TYPE"] = "Task"

        # Mock SSM client
        mock_ssm_client = mock_boto3_client.return_value
        mock_ssm_client.get_parameter.return_value = {"Parameter": {"Value": "true"}}

        # Create JiraService after mocking
        from config import Config
        from services.jira_service import JiraService

        config = Config()
        jira_service = JiraService(config)

        # Mock successful Lambda invocation
        mock_lambda_client = Mock()
        mock_lambda_client.invoke.return_value = {"StatusCode": 200, "Payload": Mock()}
        mock_lambda_client.invoke.return_value["Payload"].read.return_value = json.dumps(
            {"statusCode": 200, "body": json.dumps({"success": True, "issue_key": "SECO-124"})}
        )
        jira_service.lambda_client = mock_lambda_client

        non_human_violations = NonHumanViolations(
            total_count=1,
            by_category={"UNAUTHORIZED_ACCESS": 1},
            violations=[
                {
                    "type": "UNAUTHORIZED_ACCESS",
                    "severity": "CRITICAL",
                    "user_id": "service-account",
                    "actor_type": "SERVICE",
                    "resource_arn": "arn:aws:s3:::test-bucket",
                    "event_time": "2025-09-08 14:02:34.000",
                    "event_name": "GetObject",
                    "description": "Unauthorized access",
                    "matched_request": None,
                    "resource_details": {"s3_bucket": "test-bucket", "s3_key": "test-key"},
                    "evidence": {"source_ip": "1.2.3.4"},
                }
            ],
        )

        report_metadata = ReportMetadata(generated_at="2025-09-08T10:00:00Z", execution_duration_seconds=30.5)

        time_period = {
            "start": "2025-09-07T22:00:00Z",
            "end": "2025-09-08T21:59:59Z",
            "start_local": "2025-09-08T00:00:00+02:00",
            "end_local": "2025-09-08T23:59:59+02:00",
        }

        result = jira_service.create_non_human_violation_ticket(non_human_violations, report_metadata, time_period)

        assert result == "SECO-124"
        mock_lambda_client.invoke.assert_called_once()

        # Verify the payload structure
        call_args = mock_lambda_client.invoke.call_args
        payload = json.loads(call_args[1]["Payload"])

        assert payload["project_key"] == "PROJ"
        assert payload["issue_type"] == "Task"
        assert "audit" in payload["labels"]
        assert "cdaa" in payload["labels"]
        assert "violation" in payload["labels"]
        assert "service or unknown actor" in payload["summary"]
        assert "UNAUTHORIZED_ACCESS" in payload["description"]

    @patch("config.boto3.client")
    def test_create_ticket_lambda_error(self, mock_boto3_client):
        """Test ticket creation with Lambda error raises exception"""
        # Set required environment variables
        os.environ["JIRA_REPORTING_ENABLED_PARAM"] = "/test/jira-reporting-enabled"
        os.environ["JIRA_CONNECTOR_FUNCTION_NAME"] = "test-jira-connector"
        os.environ["JIRA_PROJECT_KEY"] = "PROJ"
        os.environ["JIRA_ISSUE_TYPE"] = "Task"

        # Mock SSM client
        mock_ssm_client = mock_boto3_client.return_value
        mock_ssm_client.get_parameter.return_value = {"Parameter": {"Value": "true"}}

        # Create JiraService after mocking
        from config import Config
        from services.jira_service import JiraService

        config = Config()
        jira_service = JiraService(config)

        # Mock Lambda error
        mock_lambda_client = Mock()
        mock_lambda_client.invoke.side_effect = Exception("Lambda error")
        jira_service.lambda_client = mock_lambda_client

        user_group = HumanViolationGroup(user_email="test@example.com", violations_count=1, violations=[])

        report_metadata = ReportMetadata(generated_at="2025-09-08T10:00:00Z", execution_duration_seconds=30.5)

        time_period = {"start": "2025-09-07T22:00:00Z", "end": "2025-09-08T21:59:59Z"}

        # Should raise RuntimeError instead of returning None
        with pytest.raises(RuntimeError, match="Failed to invoke Jira connector"):
            jira_service.create_human_violation_ticket(user_group, report_metadata, time_period)

    @patch("config.boto3.client")
    def test_create_ticket_api_error(self, mock_boto3_client):
        """Test ticket creation with API error response raises exception"""
        # Set required environment variables
        os.environ["JIRA_REPORTING_ENABLED_PARAM"] = "/test/jira-reporting-enabled"
        os.environ["JIRA_CONNECTOR_FUNCTION_NAME"] = "test-jira-connector"
        os.environ["JIRA_PROJECT_KEY"] = "PROJ"
        os.environ["JIRA_ISSUE_TYPE"] = "Task"

        # Mock SSM client
        mock_ssm_client = mock_boto3_client.return_value
        mock_ssm_client.get_parameter.return_value = {"Parameter": {"Value": "true"}}

        # Create JiraService after mocking
        from config import Config
        from services.jira_service import JiraService

        config = Config()
        jira_service = JiraService(config)

        # Mock API error response
        mock_lambda_client = Mock()
        mock_lambda_client.invoke.return_value = {"StatusCode": 200, "Payload": Mock()}
        mock_lambda_client.invoke.return_value["Payload"].read.return_value = json.dumps(
            {"statusCode": 400, "body": json.dumps({"error": "CONTENT_LIMIT_EXCEEDED"})}
        )
        jira_service.lambda_client = mock_lambda_client

        user_group = HumanViolationGroup(user_email="test@example.com", violations_count=1, violations=[])

        report_metadata = ReportMetadata(generated_at="2025-09-08T10:00:00Z", execution_duration_seconds=30.5)

        time_period = {"start": "2025-09-07T22:00:00Z", "end": "2025-09-08T21:59:59Z"}

        # Should raise RuntimeError instead of returning None
        with pytest.raises(RuntimeError, match="Jira connector failed"):
            jira_service.create_human_violation_ticket(user_group, report_metadata, time_period)

    @patch("config.boto3.client")
    def test_create_ticket_lambda_error_raises_exception(self, mock_boto3_client):
        """Test ticket creation with Lambda error raises exception"""
        # Set required environment variables
        os.environ["JIRA_REPORTING_ENABLED_PARAM"] = "/test/jira-reporting-enabled"
        os.environ["JIRA_CONNECTOR_FUNCTION_NAME"] = "test-jira-connector"
        os.environ["JIRA_PROJECT_KEY"] = "PROJ"
        os.environ["JIRA_ISSUE_TYPE"] = "Task"

        # Mock SSM client
        mock_ssm_client = mock_boto3_client.return_value
        mock_ssm_client.get_parameter.return_value = {"Parameter": {"Value": "true"}}

        # Create JiraService after mocking
        from config import Config
        from services.jira_service import JiraService

        config = Config()
        jira_service = JiraService(config)

        # Mock Lambda error
        mock_lambda_client = Mock()
        mock_lambda_client.invoke.side_effect = Exception("Lambda invocation failed")
        jira_service.lambda_client = mock_lambda_client

        user_group = HumanViolationGroup(user_email="test@example.com", violations_count=1, violations=[])

        report_metadata = ReportMetadata(generated_at="2025-09-08T10:00:00Z", execution_duration_seconds=30.5)

        time_period = {"start": "2025-09-07T22:00:00Z", "end": "2025-09-08T21:59:59Z"}

        # Should raise RuntimeError instead of returning None
        with pytest.raises(RuntimeError, match="Failed to invoke Jira connector"):
            jira_service.create_human_violation_ticket(user_group, report_metadata, time_period)

    @patch("config.boto3.client")
    def test_create_ticket_missing_function_name_raises_exception(self, mock_boto3_client):
        """Test ticket creation with missing function name raises exception"""
        # Set required environment variables
        os.environ["JIRA_REPORTING_ENABLED_PARAM"] = "/test/jira-reporting-enabled"
        os.environ["JIRA_PROJECT_KEY"] = "PROJ"
        os.environ["JIRA_ISSUE_TYPE"] = "Task"

        # Remove the function name environment variable
        if "JIRA_CONNECTOR_FUNCTION_NAME" in os.environ:
            del os.environ["JIRA_CONNECTOR_FUNCTION_NAME"]

        # Mock SSM client
        mock_ssm_client = mock_boto3_client.return_value
        mock_ssm_client.get_parameter.return_value = {"Parameter": {"Value": "true"}}

        # Create JiraService after mocking
        from config import Config
        from services.jira_service import JiraService

        config = Config()
        jira_service = JiraService(config)

        user_group = HumanViolationGroup(user_email="test@example.com", violations_count=1, violations=[])

        report_metadata = ReportMetadata(generated_at="2025-09-08T10:00:00Z", execution_duration_seconds=30.5)

        time_period = {"start": "2025-09-07T22:00:00Z", "end": "2025-09-08T21:59:59Z"}

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="JIRA_CONNECTOR_FUNCTION_NAME environment variable not set"):
            jira_service.create_human_violation_ticket(user_group, report_metadata, time_period)

    @patch("config.boto3.client")
    def test_log_ticket_data_always_logs(self, mock_boto3_client):
        """Test that ticket data is always logged regardless of Jira reporting status"""
        # Set required environment variables
        os.environ["JIRA_REPORTING_ENABLED_PARAM"] = "/test/jira-reporting-enabled"
        os.environ["JIRA_CONNECTOR_FUNCTION_NAME"] = "test-jira-connector"
        os.environ["JIRA_PROJECT_KEY"] = "PROJ"
        os.environ["JIRA_ISSUE_TYPE"] = "Task"

        # Mock SSM client
        mock_ssm_client = mock_boto3_client.return_value
        mock_ssm_client.get_parameter.return_value = {"Parameter": {"Value": "true"}}

        # Create JiraService after mocking
        from config import Config
        from services.jira_service import JiraService

        config = Config()
        jira_service = JiraService(config)

        user_group = HumanViolationGroup(user_email="test@example.com", violations_count=1, violations=[])

        report_metadata = ReportMetadata(generated_at="2025-09-08T10:00:00Z", execution_duration_seconds=30.5)

        time_period = {"start": "2025-09-07T22:00:00Z", "end": "2025-09-08T21:59:59Z"}

        # Mock successful Lambda invocation
        mock_lambda_client = Mock()
        mock_lambda_client.invoke.return_value = {"StatusCode": 200, "Payload": Mock()}
        mock_lambda_client.invoke.return_value["Payload"].read.return_value = json.dumps(
            {"statusCode": 200, "body": json.dumps({"success": True, "issue_key": "SECO-123"})}
        )
        jira_service.lambda_client = mock_lambda_client

        # Mock the logger to capture log calls
        with patch.object(jira_service.logger, "info") as mock_logger:
            result = jira_service.create_human_violation_ticket(user_group, report_metadata, time_period)

            # Should log ticket data
            mock_logger.assert_called()
            log_calls = [call[0][0] for call in mock_logger.call_args_list]
            assert any("JIRA_TICKET_DATA:" in call for call in log_calls)

            assert result == "SECO-123"


class TestViolationFormatter:
    """Test cases for Violation Formatter"""

    @pytest.fixture
    def formatter(self):
        """Create ViolationFormatter instance"""
        return ViolationFormatter()

    def test_format_human_violation_description(self, formatter):
        """Test human violation description formatting"""
        user_group = {
            "user_email": "test@example.com",
            "violations_count": 1,
            "violations": [
                {
                    "type": "ACCESS_OUTSIDE_WINDOW",
                    "severity": "MEDIUM",
                    "user_id": "test@example.com",
                    "actor_type": "HUMAN",
                    "resource_arn": "arn:aws:s3:::test-bucket",
                    "event_time": "2025-09-08 14:02:34.000",
                    "event_name": "GetObject",
                    "description": "Access outside approved time window",
                    "matched_request": {
                        "jira_issue_id": "SECO-0000",
                        "justification": "test justification",
                        "request_timestamp": "2025-09-08T14:03:19Z",
                        "duration_minutes": 15,
                    },
                    "resource_details": {"s3_bucket": "test-bucket", "s3_key": "test-key", "operation": "GetObject"},
                    "evidence": {
                        "user_email": "test@example.com",
                        "principal_id": "AROAEXAMPLEID123456:test@example.com",
                        "session_issuer": "AWSReservedSSO_example_Admin_abc123def456",
                        "source_ip": "203.0.113.1",
                        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                        "aws_region": "eu-central-1",
                        "recipient_account_id": "123456789012",
                    },
                }
            ],
        }

        report_metadata = {"report_id": "test-report", "generated_at": "2025-09-08T16:00:00Z"}

        time_period = {"start_local": "2025-09-08T16:00:00+02:00", "end_local": "2025-09-08T16:10:00+02:00"}

        description = formatter.format_human_violation_description(user_group, report_metadata, time_period)

        assert "## Customer Data Access Violation" in description
        assert "### Report Overview:" in description
        assert "**Period:** 2025-09-08T16:00:00+02:00 - 2025-09-08T16:10:00+02:00" in description
        assert "**User:** test@example.com" in description
        assert "**Violations Count:** 1" in description
        assert "### Action Required" in description
        assert "### Violations Summary" in description
        assert "| Date | Event | Resource | Resource Details | Justification |" in description

    def test_format_non_human_violation_description(self, formatter):
        """Test non-human violation description formatting"""
        non_human_violations = {
            "total_count": 1,
            "violations_count": 1,
            "by_category": {"UNAUTHORIZED_ACCESS": 1},
            "violations": [
                {
                    "type": "UNAUTHORIZED_ACCESS",
                    "severity": "CRITICAL",
                    "user_id": "service-account",
                    "actor_type": "SERVICE",
                    "resource_arn": "arn:aws:s3:::test-bucket",
                    "event_time": "2025-09-08 14:02:34.000",
                    "event_name": "GetObject",
                    "description": "Unauthorized access attempt",
                    "matched_request": None,
                    "resource_details": {"s3_bucket": "test-bucket", "s3_key": "test-key", "operation": "GetObject"},
                    "evidence": {
                        "source_ip": "1.2.3.4",
                        "user_agent": "aws-sdk-python/1.26.0",
                        "aws_region": "eu-central-1",
                        "recipient_account_id": "123456789012",
                    },
                }
            ],
        }

        report_metadata = {"report_id": "test-report", "generated_at": "2025-09-08T16:00:00Z"}

        time_period = {"start_local": "2025-09-08T16:00:00+02:00", "end_local": "2025-09-08T16:10:00+02:00"}

        description = formatter.format_non_human_violation_description(
            non_human_violations, report_metadata, time_period
        )

        assert "## Customer Data Access Violation - Service or Unknown Actor" in description
        assert "### Report Overview:" in description
        assert "**Local Period:** 2025-09-08T16:00:00+02:00 - 2025-09-08T16:10:00+02:00" in description
        assert "**Total Count:** 1" in description
        assert "### Non-Human Violations Summary:" in description
        assert "**UNAUTHORIZED_ACCESS:** 1" in description
        assert "### Note:" in description
        assert "See attached report for detailed violation information." in description

    def test_format_violation_with_null_fields(self, formatter):
        """Test violation formatting with null fields"""
        user_group = {
            "user_email": "test@example.com",
            "violations_count": 1,
            "violations": [
                {
                    "type": "ACCESS_OUTSIDE_WINDOW",
                    "severity": "MEDIUM",
                    "user_id": "test@example.com",
                    "actor_type": "HUMAN",
                    "resource_arn": "arn:aws:s3:::test-bucket",
                    "event_time": "2025-09-08 14:02:34.000",
                    "event_name": "GetObject",
                    "description": "Test violation",
                    "matched_request": None,  # Null field
                    "resource_details": {"s3_bucket": "test-bucket", "s3_key": "test-key", "operation": "GetObject"},
                    "evidence": {
                        "user_email": "test@example.com",
                        "source_ip": "203.0.113.1",
                        "user_agent": None,  # Null field
                        "aws_region": "eu-central-1",
                    },
                }
            ],
        }

        report_metadata = {"report_id": "test-report", "generated_at": "2025-09-08T16:00:00Z"}

        time_period = {"start_local": "2025-09-08T16:00:00+02:00", "end_local": "2025-09-08T16:10:00+02:00"}

        description = formatter.format_human_violation_description(user_group, report_metadata, time_period)

        # Should include basic structure
        assert "## Customer Data Access Violation" in description
        assert "### Report Overview:" in description
        assert "**User:** test@example.com" in description
        assert "**Violations Count:** 1" in description
        assert "### Action Required" in description
        assert "### Violations Summary" in description


if __name__ == "__main__":
    pytest.main([__file__])
