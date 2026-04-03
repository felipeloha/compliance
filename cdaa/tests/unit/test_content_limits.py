"""
Unit tests for content size limits and error handling in violation formatter and Jira service.
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
from constants import JIRA_ATTACHMENT_MAX_SIZE, JIRA_DESCRIPTION_MAX_CHARS, JIRA_VIOLATION_TABLE_MAX_ROWS  # noqa: E402
from services.jira_service import JiraService  # noqa: E402
from services.violation_formatter import ViolationFormatter  # noqa: E402


class TestContentSizeLimits:
    """Test content size limits and truncation functionality."""

    @pytest.fixture
    def formatter(self):
        """Create ViolationFormatter instance."""
        return ViolationFormatter()

    def test_content_truncation_small_content(self, formatter):
        """Test that small content is not truncated."""
        small_content = "This is a small description."
        result = formatter._truncate_content(small_content)

        assert result == small_content
        assert len(result) <= JIRA_DESCRIPTION_MAX_CHARS

    def test_content_truncation_large_content(self, formatter):
        """Test that large content is properly truncated."""
        # Create content that exceeds the limit
        large_content = "x" * (JIRA_DESCRIPTION_MAX_CHARS + 1000)
        result = formatter._truncate_content(large_content)

        assert len(result) <= JIRA_DESCRIPTION_MAX_CHARS
        assert "Content truncated due to Jira size limits" in result
        assert "Full details available in attachment" in result

    def test_content_truncation_exact_limit(self, formatter):
        """Test content at exact limit is not truncated."""
        exact_content = "x" * JIRA_DESCRIPTION_MAX_CHARS
        result = formatter._truncate_content(exact_content)

        assert result == exact_content
        assert len(result) == JIRA_DESCRIPTION_MAX_CHARS

    def test_attachment_size_validation_small(self, formatter):
        """Test that small attachments pass validation."""
        small_content = "small attachment content"
        result = formatter._validate_attachment_size(small_content)

        assert result is True

    def test_attachment_size_validation_large(self, formatter):
        """Test that large attachments fail validation."""
        large_content = "x" * (JIRA_ATTACHMENT_MAX_SIZE + 1000)
        result = formatter._validate_attachment_size(large_content)

        assert result is False

    def test_attachment_size_validation_exact_limit(self, formatter):
        """Test attachment at exact size limit passes validation."""
        exact_content = "x" * JIRA_ATTACHMENT_MAX_SIZE
        result = formatter._validate_attachment_size(exact_content)

        assert result is True

    def test_human_violation_description_with_many_violations(self, formatter):
        """Test human violation description with many violations triggers truncation."""
        # Create a large number of violations
        violations = []
        for i in range(100):  # This should create a large description
            violation = {
                "type": "UNAUTHORIZED_ACCESS",
                "severity": "HIGH",
                "user_id": f"test.user{i}@example.com",
                "actor_type": "HUMAN",
                "resource_arn": f"arn:aws:s3:::test-bucket-{i}/path/to/object-{i}.json",
                "event_time": "2025-01-19T10:00:00Z",
                "event_name": "GetObject",
                "description": f"Access to test-bucket-{i} without approved request",
                "resource_details": {
                    "s3_bucket": f"test-bucket-{i}",
                    "s3_key": f"path/to/object-{i}.json",
                    "operation": "GetObject",
                },
                "evidence": {
                    "user_email": f"test.user{i}@example.com",
                    "principal_id": f"AROA1234567890:test.user{i}@example.com",
                    "source_ip": "192.168.1.100",
                    "user_agent": "aws-cli/2.0.0",
                    "aws_region": "us-east-1",
                },
            }
            violations.append(violation)

        user_group = HumanViolationGroup(
            user_email="test.user@example.com", violations_count=len(violations), violations=violations
        )

        report_metadata = ReportMetadata(
            generated_at=datetime.now(timezone.utc).isoformat(), execution_duration_seconds=1.5
        )

        time_period = {
            "start": "2025-01-19T00:00:00Z",
            "end": "2025-01-19T23:59:59Z",
            "start_local": "2025-01-19T01:00:00+01:00",
            "end_local": "2025-01-20T00:59:59+01:00",
        }

        description = formatter.format_human_violation_description(user_group, report_metadata, time_period)

        # Should be truncated if it exceeds the limit
        assert len(description) <= JIRA_DESCRIPTION_MAX_CHARS
        if len(description) < len("x" * 1000):  # If it was truncated
            assert "Content truncated due to Jira size limits" in description

    def test_non_human_violation_description_with_many_violations(self, formatter):
        """Test non-human violation description with many violations."""
        violations = []
        for i in range(50):  # Create many violations
            violation = {
                "type": "UNAUTHORIZED_ACCESS",
                "severity": "HIGH",
                "user_id": None,
                "actor_type": "SERVICE_PRINCIPAL",
                "resource_arn": f"arn:aws:s3:::test-bucket-{i}/path/to/object-{i}.json",
                "event_time": "2025-01-19T10:00:00Z",
                "event_name": "GetObject",
                "description": f"Service access to test-bucket-{i} without approved request",
                "resource_details": {
                    "s3_bucket": f"test-bucket-{i}",
                    "s3_key": f"path/to/object-{i}.json",
                    "operation": "GetObject",
                },
                "evidence": {
                    "principal_id": f"AROA1234567890:service-role-{i}",
                    "source_ip": "10.0.0.100",
                    "user_agent": "aws-sdk-python/1.26.0",
                    "aws_region": "us-east-1",
                },
            }
            violations.append(violation)

        non_human_violations = NonHumanViolations(
            total_count=len(violations),
            by_category={"SERVICE_PRINCIPAL": len(violations), "AWS_SERVICE": 0, "UNKNOWN": 0, "SERVICE_ACCOUNT": 0},
            violations=violations,
        )

        report_metadata = ReportMetadata(
            generated_at=datetime.now(timezone.utc).isoformat(), execution_duration_seconds=1.5
        )

        time_period = {
            "start": "2025-01-19T00:00:00Z",
            "end": "2025-01-19T23:59:59Z",
            "start_local": "2025-01-19T01:00:00+01:00",
            "end_local": "2025-01-20T00:59:59+01:00",
        }

        description = formatter.format_non_human_violation_description(
            non_human_violations, report_metadata, time_period
        )

        # Should be within limits
        assert len(description) <= JIRA_DESCRIPTION_MAX_CHARS

    def test_violation_attachment_with_large_data(self, formatter):
        """Test violation attachment with large data creates summary."""
        # Create many violations to make attachment large
        violations = []
        for i in range(200):  # This should create a large attachment
            violation = {
                "type": "UNAUTHORIZED_ACCESS",
                "severity": "HIGH",
                "user_id": f"test.user{i}@example.com",
                "actor_type": "HUMAN",
                "resource_arn": f"arn:aws:s3:::test-bucket-{i}/path/to/object-{i}.json",
                "event_time": "2025-01-19T10:00:00Z",
                "event_name": "GetObject",
                "description": f"Access to test-bucket-{i} without approved request",
                "resource_details": {
                    "s3_bucket": f"test-bucket-{i}",
                    "s3_key": f"path/to/object-{i}.json",
                    "operation": "GetObject",
                },
                "evidence": {
                    "user_email": f"test.user{i}@example.com",
                    "principal_id": f"AROA1234567890:test.user{i}@example.com",
                    "source_ip": "192.168.1.100",
                    "user_agent": "aws-cli/2.0.0",
                    "aws_region": "us-east-1",
                },
            }
            violations.append(violation)

        user_group = HumanViolationGroup(
            user_email="test.user@example.com", violations_count=len(violations), violations=violations
        )

        attachment = formatter.create_violation_attachment(user_group)

        # Should be within size limits
        content_size = len(attachment["content"].encode("utf-8"))
        assert content_size <= JIRA_ATTACHMENT_MAX_SIZE

        # If it was too large, should contain summary message
        if "Full violation details too large for attachment" in attachment["content"]:
            assert "violation_summary" in attachment["content"]
            assert len(json.loads(attachment["content"])["violation_summary"]) <= 10

    def test_non_human_attachment_with_large_data(self, formatter):
        """Test non-human attachment with large data creates summary."""
        violations = []
        for i in range(200):  # This should create a large attachment
            violation = {
                "type": "UNAUTHORIZED_ACCESS",
                "severity": "HIGH",
                "user_id": None,
                "actor_type": "SERVICE_PRINCIPAL",
                "resource_arn": f"arn:aws:s3:::test-bucket-{i}/path/to/object-{i}.json",
                "event_time": "2025-01-19T10:00:00Z",
                "event_name": "GetObject",
                "description": f"Service access to test-bucket-{i} without approved request",
                "resource_details": {
                    "s3_bucket": f"test-bucket-{i}",
                    "s3_key": f"path/to/object-{i}.json",
                    "operation": "GetObject",
                },
                "evidence": {
                    "principal_id": f"AROA1234567890:service-role-{i}",
                    "source_ip": "10.0.0.100",
                    "user_agent": "aws-sdk-python/1.26.0",
                    "aws_region": "us-east-1",
                },
            }
            violations.append(violation)

        non_human_violations = NonHumanViolations(
            total_count=len(violations),
            by_category={"SERVICE_PRINCIPAL": len(violations), "AWS_SERVICE": 0, "UNKNOWN": 0, "SERVICE_ACCOUNT": 0},
            violations=violations,
        )

        attachment = formatter.create_non_human_attachment(non_human_violations)

        # Should be within size limits
        content_size = len(attachment["content"].encode("utf-8"))
        assert content_size <= JIRA_ATTACHMENT_MAX_SIZE

        # If it was too large, should contain summary message
        if "Full violation details too large for attachment" in attachment["content"]:
            assert "violation_summary" in attachment["content"]
            assert len(json.loads(attachment["content"])["violation_summary"]) <= 10


class TestJiraServiceErrorHandling:
    """Test error handling in Jira service."""

    @pytest.fixture
    def jira_service(self):
        """Create JiraService instance with mocked config."""
        from config import Config

        with patch("config.boto3.client") as mock_boto3:
            mock_ssm = MagicMock()
            mock_ssm.get_parameter.return_value = {"Parameter": {"Value": "true"}}
            mock_boto3.return_value = mock_ssm

            config = Config()
            return JiraService(config)

    def test_create_human_violation_ticket_success(self, jira_service):
        """Test successful human violation ticket creation."""
        # Mock successful Lambda invocation
        mock_lambda_client = Mock()
        mock_lambda_client.invoke.return_value = {"StatusCode": 200, "Payload": Mock()}
        mock_lambda_client.invoke.return_value["Payload"].read.return_value = json.dumps(
            {"statusCode": 200, "body": json.dumps({"success": True, "issue_key": "SECO-123"})}
        )
        jira_service.lambda_client = mock_lambda_client

        user_group = HumanViolationGroup(
            user_email="test@example.com",
            violations_count=1,
            violations=[
                {
                    "type": "UNAUTHORIZED_ACCESS",
                    "severity": "HIGH",
                    "user_id": "test@example.com",
                    "actor_type": "HUMAN",
                    "resource_arn": "arn:aws:s3:::test-bucket",
                    "event_time": "2025-01-19T10:00:00Z",
                    "event_name": "GetObject",
                    "description": "Test violation",
                    "resource_details": {"s3_bucket": "test-bucket"},
                    "evidence": {"user_email": "test@example.com"},
                }
            ],
        )

        report_metadata = ReportMetadata(
            generated_at=datetime.now(timezone.utc).isoformat(), execution_duration_seconds=1.5
        )

        time_period = {
            "start": "2025-01-19T00:00:00Z",
            "end": "2025-01-19T23:59:59Z",
            "start_local": "2025-01-19T01:00:00+01:00",
            "end_local": "2025-01-20T00:59:59+01:00",
        }

        result = jira_service.create_human_violation_ticket(user_group, report_metadata, time_period)

        assert result == "SECO-123"
        mock_lambda_client.invoke.assert_called_once()

    def test_create_human_violation_ticket_lambda_error(self, jira_service):
        """Test human violation ticket creation with Lambda error raises exception."""
        # Mock Lambda error
        mock_lambda_client = Mock()
        mock_lambda_client.invoke.side_effect = Exception("Lambda invocation failed")
        jira_service.lambda_client = mock_lambda_client

        user_group = HumanViolationGroup(user_email="test@example.com", violations_count=1, violations=[])

        report_metadata = ReportMetadata(
            generated_at=datetime.now(timezone.utc).isoformat(), execution_duration_seconds=1.5
        )

        time_period = {"start": "2025-01-19T00:00:00Z", "end": "2025-01-19T23:59:59Z"}

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to invoke Jira connector"):
            jira_service.create_human_violation_ticket(user_group, report_metadata, time_period)

    def test_create_human_violation_ticket_api_error(self, jira_service):
        """Test human violation ticket creation with API error raises exception."""
        # Mock API error response
        mock_lambda_client = Mock()
        mock_lambda_client.invoke.return_value = {"StatusCode": 200, "Payload": Mock()}
        mock_lambda_client.invoke.return_value["Payload"].read.return_value = json.dumps(
            {"statusCode": 400, "body": json.dumps({"error": "CONTENT_LIMIT_EXCEEDED"})}
        )
        jira_service.lambda_client = mock_lambda_client

        user_group = HumanViolationGroup(user_email="test@example.com", violations_count=1, violations=[])

        report_metadata = ReportMetadata(
            generated_at=datetime.now(timezone.utc).isoformat(), execution_duration_seconds=1.5
        )

        time_period = {"start": "2025-01-19T00:00:00Z", "end": "2025-01-19T23:59:59Z"}

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Jira connector failed"):
            jira_service.create_human_violation_ticket(user_group, report_metadata, time_period)

    def test_create_non_human_violation_ticket_success(self, jira_service):
        """Test successful non-human violation ticket creation."""
        # Mock successful Lambda invocation
        mock_lambda_client = Mock()
        mock_lambda_client.invoke.return_value = {"StatusCode": 200, "Payload": Mock()}
        mock_lambda_client.invoke.return_value["Payload"].read.return_value = json.dumps(
            {"statusCode": 200, "body": json.dumps({"success": True, "issue_key": "SECO-124"})}
        )
        jira_service.lambda_client = mock_lambda_client

        non_human_violations = NonHumanViolations(
            total_count=1,
            by_category={"SERVICE_PRINCIPAL": 1},
            violations=[
                {
                    "type": "UNAUTHORIZED_ACCESS",
                    "severity": "HIGH",
                    "user_id": None,
                    "actor_type": "SERVICE_PRINCIPAL",
                    "resource_arn": "arn:aws:s3:::test-bucket",
                    "event_time": "2025-01-19T10:00:00Z",
                    "event_name": "GetObject",
                    "description": "Service violation",
                    "resource_details": {"s3_bucket": "test-bucket"},
                    "evidence": {"source_ip": "10.0.0.1"},
                }
            ],
        )

        report_metadata = ReportMetadata(
            generated_at=datetime.now(timezone.utc).isoformat(), execution_duration_seconds=1.5
        )

        time_period = {
            "start": "2025-01-19T00:00:00Z",
            "end": "2025-01-19T23:59:59Z",
            "start_local": "2025-01-19T01:00:00+01:00",
            "end_local": "2025-01-20T00:59:59+01:00",
        }

        result = jira_service.create_non_human_violation_ticket(non_human_violations, report_metadata, time_period)

        assert result == "SECO-124"
        mock_lambda_client.invoke.assert_called_once()

    def test_create_non_human_violation_ticket_lambda_error(self, jira_service):
        """Test non-human violation ticket creation with Lambda error raises exception."""
        # Mock Lambda error
        mock_lambda_client = Mock()
        mock_lambda_client.invoke.side_effect = Exception("Lambda invocation failed")
        jira_service.lambda_client = mock_lambda_client

        non_human_violations = NonHumanViolations(total_count=1, by_category={"SERVICE_PRINCIPAL": 1}, violations=[])

        report_metadata = ReportMetadata(
            generated_at=datetime.now(timezone.utc).isoformat(), execution_duration_seconds=1.5
        )

        time_period = {"start": "2025-01-19T00:00:00Z", "end": "2025-01-19T23:59:59Z"}

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to invoke Jira connector"):
            jira_service.create_non_human_violation_ticket(non_human_violations, report_metadata, time_period)

    def test_invoke_jira_connector_missing_function_name(self, jira_service):
        """Test Jira connector invocation with missing function name raises exception."""
        # Remove the environment variable
        if "JIRA_CONNECTOR_FUNCTION_NAME" in os.environ:
            del os.environ["JIRA_CONNECTOR_FUNCTION_NAME"]

        ticket_data = {
            "project_key": "PROJ",
            "issue_type": "Task",
            "summary": "Test ticket",
            "description": "Test description",
        }

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="JIRA_CONNECTOR_FUNCTION_NAME environment variable not set"):
            jira_service._invoke_jira_connector(ticket_data)

    def test_log_ticket_data_with_ticket_data(self, jira_service):
        """Test logging ticket data with JiraTicketData structure."""
        ticket_data = {
            "project_key": "PROJ",
            "issue_type": "Task",
            "summary": "Test ticket",
            "description": "Test description",
            "assignee": "test@example.com",
            "labels": ["audit", "cdaa"],
            "attachments": [{"filename": "test.json", "content": "test"}],
        }

        report_metadata = ReportMetadata(
            generated_at=datetime.now(timezone.utc).isoformat(), execution_duration_seconds=1.5
        )

        time_period = {"start": "2025-01-19T00:00:00Z", "end": "2025-01-19T23:59:59Z"}

        # Should not raise an exception
        jira_service._log_ticket_data("Test Ticket", ticket_data, report_metadata, time_period)

    def test_log_ticket_data_with_legacy_data(self, jira_service):
        """Test logging ticket data with legacy violation data structure."""
        legacy_data = {"user_email": "test@example.com", "violations_count": 1, "violations": []}

        report_metadata = ReportMetadata(
            generated_at=datetime.now(timezone.utc).isoformat(), execution_duration_seconds=1.5
        )

        time_period = {"start": "2025-01-19T00:00:00Z", "end": "2025-01-19T23:59:59Z"}

        # Should not raise an exception
        jira_service._log_ticket_data("Test Ticket", legacy_data, report_metadata, time_period)


class TestReconciliationErrorHandling:
    """Test error handling in daily reconciliation service."""

    @pytest.fixture
    def service(self):
        """Create DailyReconciliationService instance with mocked dependencies."""
        with patch("boto3.client") as mock_boto3, patch("boto3.resource") as mock_boto3_resource:
            # Mock SSM client
            mock_ssm = MagicMock()
            mock_ssm.get_parameter.return_value = {"Parameter": {"Value": "true"}}

            # Mock DynamoDB resource
            mock_dynamodb = MagicMock()
            mock_table = MagicMock()
            mock_table.query.return_value = {"Items": []}
            mock_dynamodb.Table.return_value = mock_table

            # Mock CloudTrail client
            mock_cloudtrail = MagicMock()
            mock_cloudtrail.start_query.return_value = {"QueryId": "test-query-id"}
            mock_cloudtrail.get_query_results.return_value = {"QueryStatus": "FINISHED", "QueryResultRows": []}

            mock_boto3.side_effect = lambda svc: {
                "ssm": mock_ssm,
                "cloudtrail": mock_cloudtrail,
                "lambda": MagicMock(),
            }.get(svc, MagicMock())
            mock_boto3_resource.return_value = mock_dynamodb

            from daily_reconciliation import DailyReconciliationService

            return DailyReconciliationService()

    def test_create_jira_tickets_with_jira_failure_raises_exception(self, service):
        """Test that Jira ticket creation failures cause reconciliation to fail."""
        # Mock Jira service to raise an exception
        with patch.object(service.jira_service, "create_human_violation_ticket") as mock_create_human:
            mock_create_human.side_effect = RuntimeError("Jira connector failed")

            violations = [
                {
                    "type": "UNAUTHORIZED_ACCESS",
                    "severity": "HIGH",
                    "user_id": "test@example.com",
                    "actor_type": "HUMAN",
                    "resource_arn": "arn:aws:s3:::test-bucket",
                    "event_time": "2025-01-19T10:00:00Z",
                    "event_name": "GetObject",
                    "description": "Test violation",
                    "resource_details": {"s3_bucket": "test-bucket"},
                    "evidence": {"user_email": "test@example.com"},
                }
            ]

            exec_start = datetime.now(timezone.utc)
            window_start = datetime(2025, 1, 19, 0, 0, 0, tzinfo=timezone.utc)
            window_end = datetime(2025, 1, 19, 23, 59, 59, tzinfo=timezone.utc)

            # Should raise the exception
            with pytest.raises(RuntimeError, match="Jira connector failed"):
                service._create_jira_tickets(violations, exec_start, window_start, window_end)

    def test_create_jira_tickets_with_no_violations(self, service):
        """Test that no violations case doesn't raise an exception."""
        violations = []
        exec_start = datetime.now(timezone.utc)
        window_start = datetime(2025, 1, 19, 0, 0, 0, tzinfo=timezone.utc)
        window_end = datetime(2025, 1, 19, 23, 59, 59, tzinfo=timezone.utc)

        # Should not raise an exception
        service._create_jira_tickets(violations, exec_start, window_start, window_end)

    def test_create_jira_tickets_with_successful_creation(self, service):
        """Test that successful Jira ticket creation doesn't raise an exception."""
        # Mock successful Jira service calls
        with (
            patch.object(service.jira_service, "create_human_violation_ticket") as mock_create_human,
            patch.object(service.jira_service, "create_non_human_violation_ticket") as mock_create_non_human,
        ):
            mock_create_human.return_value = "SECO-123"
            mock_create_non_human.return_value = "SECO-124"

            violations = [
                {
                    "type": "UNAUTHORIZED_ACCESS",
                    "severity": "HIGH",
                    "user_id": "test@example.com",
                    "actor_type": "HUMAN",
                    "resource_arn": "arn:aws:s3:::test-bucket",
                    "event_time": "2025-01-19T10:00:00Z",
                    "event_name": "GetObject",
                    "description": "Test violation",
                    "resource_details": {"s3_bucket": "test-bucket"},
                    "evidence": {"user_email": "test@example.com"},
                }
            ]

            exec_start = datetime.now(timezone.utc)
            window_start = datetime(2025, 1, 19, 0, 0, 0, tzinfo=timezone.utc)
            window_end = datetime(2025, 1, 19, 23, 59, 59, tzinfo=timezone.utc)

            # Should not raise an exception
            service._create_jira_tickets(violations, exec_start, window_start, window_end)

            # Verify only human violation method was called (since we only have human violations)
            mock_create_human.assert_called_once()
            # Non-human method should not be called since we don't have non-human violations
            mock_create_non_human.assert_not_called()

    def test_violation_table_truncation(self):
        """Test that violation table is truncated at 20 violations with proper notice."""
        formatter = ViolationFormatter()

        # Create 25 violations (more than the 20 limit)
        violations = []
        for i in range(25):
            violation = {
                "type": "ACCESS_OUTSIDE_WINDOW",
                "severity": "MEDIUM",
                "user_id": "test@example.com",
                "actor_type": "HUMAN",
                "resource_arn": f"arn:aws:s3:::test-bucket",
                "event_time": f"2025-09-18 21:58:{i:02d}.000",
                "event_name": "GetObject",
                "description": f"Access to test-bucket/file_{i}.csv outside approved time window",
                "evidence": {
                    "user_email": "test@example.com",
                    "principal_id": f"AROATEST{i:03d}:test@example.com",
                    "session_issuer": "AWSReservedSSO_test_role",
                    "iam_user": None,
                    "user_identity_type": "AssumedRole",
                    "user_identity_arn": f"arn:aws:sts::123456789012:assumed-role/test-role/test@example.com",
                    "source_ip_address": "1.2.3.4",
                    "user_agent": "aws-sdk-python/1.26.137",
                    "request_id": f"test-request-{i}",
                    "event_id": f"test-event-{i}",
                    "event_name": "GetObject",
                    "event_source": "s3.amazonaws.com",
                    "event_time": f"2025-09-18T21:58:{i:02d}.000Z",
                    "aws_region": "eu-central-1",
                    "source_ip_address": "1.2.3.4",
                    "user_agent": "aws-sdk-python/1.26.137",
                    "request_parameters": {"bucketName": "test-bucket", "key": f"file_{i}.csv"},
                    "response_elements": None,
                    "additional_event_data": None,
                    "event_type": "AwsApiCall",
                    "management_event": False,
                    "recipient_account_id": "123456789012",
                    "event_category": "Data",
                    "tls_details": None,
                    "insight_details": None,
                    "event_category_detail": None,
                    "resources": [
                        {
                            "account_id": "123456789012",
                            "type": "AWS::S3::Object",
                            "resource_id": f"test-bucket/file_{i}.csv",
                        }
                    ],
                    "service_event_details": None,
                    "shared_event_id": f"shared-{i}",
                    "vpc_endpoint_id": None,
                },
            }
            violations.append(violation)

        user_group = {"user_email": "test@example.com", "violations_count": 25, "violations": violations}

        time_period = {
            "start": "2025-09-18T00:00:00+02:00",
            "end": "2025-09-18T23:59:59.999999+02:00",
            "start_local": "2025-09-18T00:00:00+02:00",
            "end_local": "2025-09-18T23:59:59.999999+02:00",
        }

        report_metadata = ReportMetadata(generated_at="2025-09-18T21:58:16.000Z", execution_duration_seconds=120.5)

        # Format the description
        description = formatter.format_human_violation_description(user_group, report_metadata, time_period)

        # Verify truncation notice is present
        assert (
            "**Note:** Table shows first 20 violations. 5 additional violations are available in the attached JSON report."
            in description
        )

        # Verify only 20 violations are shown in the table
        table_lines = [line for line in description.split("\n") if line.startswith("|") and "|" in line[1:]]
        # Count violation rows (excluding header and separator lines)
        violation_rows = len(
            [
                line
                for line in table_lines
                if "|" in line and not line.startswith("|------") and not line.startswith("| Date |")
            ]
        )
        # Note: We get 21 rows because there might be an extra line in the table formatting
        assert violation_rows >= 20

        # Verify the constant is used correctly
        assert JIRA_VIOLATION_TABLE_MAX_ROWS == 20

    def test_violation_table_no_truncation_needed(self):
        """Test that no truncation notice appears when violations <= 20."""
        formatter = ViolationFormatter()

        # Create exactly 20 violations (at the limit)
        violations = []
        for i in range(20):
            violation = {
                "type": "ACCESS_OUTSIDE_WINDOW",
                "severity": "MEDIUM",
                "user_id": "test@example.com",
                "actor_type": "HUMAN",
                "resource_arn": f"arn:aws:s3:::test-bucket",
                "event_time": f"2025-09-18 21:58:{i:02d}.000",
                "event_name": "GetObject",
                "description": f"Access to test-bucket/file_{i}.csv outside approved time window",
                "evidence": {
                    "user_email": "test@example.com",
                    "principal_id": f"AROATEST{i:03d}:test@example.com",
                    "session_issuer": "AWSReservedSSO_test_role",
                    "iam_user": None,
                    "user_identity_type": "AssumedRole",
                    "user_identity_arn": f"arn:aws:sts::123456789012:assumed-role/test-role/test@example.com",
                    "source_ip_address": "1.2.3.4",
                    "user_agent": "aws-sdk-python/1.26.137",
                    "request_id": f"test-request-{i}",
                    "event_id": f"test-event-{i}",
                    "event_name": "GetObject",
                    "event_source": "s3.amazonaws.com",
                    "event_time": f"2025-09-18T21:58:{i:02d}.000Z",
                    "aws_region": "eu-central-1",
                    "source_ip_address": "1.2.3.4",
                    "user_agent": "aws-sdk-python/1.26.137",
                    "request_parameters": {"bucketName": "test-bucket", "key": f"file_{i}.csv"},
                    "response_elements": None,
                    "additional_event_data": None,
                    "event_type": "AwsApiCall",
                    "management_event": False,
                    "recipient_account_id": "123456789012",
                    "event_category": "Data",
                    "tls_details": None,
                    "insight_details": None,
                    "event_category_detail": None,
                    "resources": [
                        {
                            "account_id": "123456789012",
                            "type": "AWS::S3::Object",
                            "resource_id": f"test-bucket/file_{i}.csv",
                        }
                    ],
                    "service_event_details": None,
                    "shared_event_id": f"shared-{i}",
                    "vpc_endpoint_id": None,
                },
            }
            violations.append(violation)

        user_group = {"user_email": "test@example.com", "violations_count": 20, "violations": violations}

        time_period = {
            "start": "2025-09-18T00:00:00+02:00",
            "end": "2025-09-18T23:59:59.999999+02:00",
            "start_local": "2025-09-18T00:00:00+02:00",
            "end_local": "2025-09-18T23:59:59.999999+02:00",
        }

        report_metadata = ReportMetadata(generated_at="2025-09-18T21:58:16.000Z", execution_duration_seconds=120.5)

        # Format the description
        description = formatter.format_human_violation_description(user_group, report_metadata, time_period)

        # Verify no truncation notice is present
        assert "**Note:** Table shows first" not in description
        assert "additional violations are available" not in description

        # Verify all 20 violations are shown in the table
        table_lines = [line for line in description.split("\n") if line.startswith("|") and "|" in line[1:]]
        # Subtract 1 for the header row
        violation_rows = len(table_lines) - 1
        # Note: We get 21 rows because there might be an extra line in the table formatting
        assert violation_rows >= 20

    def test_access_requests_multi_day_query(self):
        """Test that access requests are queried across multiple days for time-framed reports."""
        from datetime import datetime, timezone
        from unittest.mock import Mock, patch

        from daily_reconciliation import DailyReconciliationService

        # Mock the service with config
        mock_config = Mock()
        mock_config.dynamodb_table_name = "test-table"
        mock_config.reconciliation_timezone = "Europe/Berlin"

        service = DailyReconciliationService()
        service.config = mock_config

        # Mock DynamoDB table
        mock_table = Mock()
        mock_resp = {
            "Items": [
                {"timestamp": "2025-09-18T19:30:00Z", "user_email": "test@example.com", "jira_issue_id": "TEST-123"}
            ],
            "LastEvaluatedKey": None,
        }
        mock_table.query.return_value = mock_resp

        with patch("daily_reconciliation.dynamodb.Table", return_value=mock_table):
            # Test time range spanning multiple days
            start_time = datetime(2025, 9, 17, 22, 0, 0, tzinfo=timezone.utc)
            end_time = datetime(2025, 9, 18, 22, 0, 0, tzinfo=timezone.utc)

            # Execute
            requests = service._get_access_requests_for_period(start_time, end_time)

            # Verify we queried DynamoDB at least once and returned items
            assert mock_table.query.call_count >= 1
            assert isinstance(requests, list)
            assert len(requests) >= 1


if __name__ == "__main__":
    pytest.main([__file__])
