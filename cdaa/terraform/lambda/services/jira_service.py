#!/usr/bin/env python3
"""
Jira integration service for Customer Data Access Audit (CDAA) system.
"""

import base64
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from audit_types import HumanViolationGroup, JiraTicketData, NonHumanViolations, ReportMetadata
from constants import JIRA_ISSUE_TYPE, JIRA_LABELS

from .violation_formatter import ViolationFormatter

logger = logging.getLogger(__name__)


class JiraService:
    """Service for creating Jira tickets for violations."""

    def __init__(self, config):
        self.config = config
        self.formatter = ViolationFormatter()
        self.lambda_client = boto3.client("lambda")
        self.logger = logger

    def _format_date_range_for_title(self, time_period: Dict[str, str]) -> str:
        """Format date range for ticket title (start - end, up to minutes)."""
        try:
            start_local = time_period.get("start_local", "N/A")
            end_local = time_period.get("end_local", "N/A")

            if start_local == "N/A" or end_local == "N/A":
                return start_local

            # Parse the datetime strings and format to show only up to minutes
            start_dt = datetime.fromisoformat(start_local.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_local.replace("Z", "+00:00"))

            # Format as YYYY-MM-DDTHH:MM - YYYY-MM-DDTHH:MM
            start_formatted = start_dt.strftime("%Y-%m-%dT%H:%M")
            end_formatted = end_dt.strftime("%Y-%m-%dT%H:%M")

            return f"{start_formatted} - {end_formatted}"

        except Exception as e:
            self.logger.warning(f"Failed to format date range for title: {e}")
            return time_period.get("start_local", "N/A")

    def create_human_violation_ticket(
        self, user_group: HumanViolationGroup, report_metadata: ReportMetadata, time_period: Dict[str, str]
    ) -> Optional[str]:
        """Create a Jira ticket for human violations."""
        try:
            description = self.formatter.format_human_violation_description(user_group, report_metadata, time_period)

            attachment_data = self.formatter.create_violation_attachment(user_group)
            attachment_content = base64.b64encode(attachment_data["content"].encode("utf-8")).decode("utf-8")

            date_range = self._format_date_range_for_title(time_period)
            ticket_data = JiraTicketData(
                project_key=self.config.jira_project_key,
                issue_type=self.config.jira_issue_type,
                summary=f"Customer data access violation - {user_group['user_email']} - {date_range}",
                description=description,
                assignee=user_group["user_email"],
                labels=JIRA_LABELS,
                attachments=[{"filename": attachment_data["filename"], "content": attachment_content}],
            )

            # Always log ticket data regardless of Jira reporting status
            self._log_ticket_data("Human Violation Ticket", ticket_data, report_metadata, time_period)

            if not self.config.jira_reporting_enabled:
                self.logger.info("Jira reporting disabled - ticket data logged only")
                return None

            return self._invoke_jira_connector(ticket_data)

        except Exception as e:
            self.logger.error(f"Failed to create human violation ticket: {e}")
            raise  # Re-raise to fail the reconciliation

    def create_non_human_violation_ticket(
        self, non_human_violations: NonHumanViolations, report_metadata: ReportMetadata, time_period: Dict[str, str]
    ) -> Optional[str]:
        """Create a Jira ticket for non-human violations."""
        try:
            description = self.formatter.format_non_human_violation_description(
                non_human_violations, report_metadata, time_period
            )

            attachment_data = self.formatter.create_non_human_attachment(non_human_violations)
            attachment_content = base64.b64encode(attachment_data["content"].encode("utf-8")).decode("utf-8")

            date_range = self._format_date_range_for_title(time_period)
            ticket_data = JiraTicketData(
                project_key=self.config.jira_project_key,
                issue_type=self.config.jira_issue_type,
                summary=f"Customer data access violation - service or unknown actor - {date_range}",
                description=description,
                assignee=None,  # No assignee for non-human violations
                labels=JIRA_LABELS,
                attachments=[{"filename": attachment_data["filename"], "content": attachment_content}],
            )

            # Always log ticket data regardless of Jira reporting status
            self._log_ticket_data("Non-Human Violation Ticket", ticket_data, report_metadata, time_period)

            if not self.config.jira_reporting_enabled:
                self.logger.info("Jira reporting disabled - ticket data logged only")
                return None

            return self._invoke_jira_connector(ticket_data)

        except Exception as e:
            self.logger.error(f"Failed to create non-human violation ticket: {e}")
            raise  # Re-raise to fail the reconciliation

    def _invoke_jira_connector(self, ticket_data: JiraTicketData) -> Optional[str]:
        """Invoke the Jira connector Lambda function."""
        try:
            # Get the Jira connector Lambda function name from environment
            jira_connector_function = os.environ.get("JIRA_CONNECTOR_FUNCTION_NAME")
            if not jira_connector_function:
                error_msg = "JIRA_CONNECTOR_FUNCTION_NAME environment variable not set"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

            response = self.lambda_client.invoke(
                FunctionName=jira_connector_function, InvocationType="RequestResponse", Payload=json.dumps(ticket_data)
            )

            result = json.loads(response["Payload"].read())

            if result.get("statusCode") == 200:
                body = json.loads(result["body"])
                issue_key = body.get("issue_key")
                self.logger.info(f"Successfully created Jira ticket: {issue_key}")
                return issue_key
            else:
                error_msg = f"Jira connector failed: {result}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

        except Exception as e:
            error_msg = f"Failed to invoke Jira connector: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def _log_ticket_data(
        self, ticket_type: str, data: Any, report_metadata: ReportMetadata, time_period: Dict[str, str]
    ) -> None:
        """Log ticket data for all tickets (enabled or disabled Jira reporting)."""
        # Extract key information for logging
        if isinstance(data, dict) and "project_key" in data:
            # This is a JiraTicketData object
            ticket_info = {
                "ticket_type": ticket_type,
                "project_key": data.get("project_key"),
                "issue_type": data.get("issue_type"),
                "summary": data.get("summary"),
                "assignee": data.get("assignee"),
                "labels": data.get("labels"),
                "description_length": len(data.get("description", "")),
                "attachments_count": len(data.get("attachments", [])),
                "report_metadata": report_metadata,
                "time_period": time_period,
            }
        else:
            # This is raw violation data (legacy format)
            ticket_info = {
                "ticket_type": ticket_type,
                "data": data,
                "report_metadata": report_metadata,
                "time_period": time_period,
            }

        self.logger.info(f"JIRA_TICKET_DATA: {json.dumps(ticket_info, default=str)}")
