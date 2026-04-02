#!/usr/bin/env python3
"""
Violation formatting service for Customer Data Access Audit (CDAA) system.
"""

import json
import logging
from typing import Any, Dict, List

from audit_types import HumanViolationGroup, NonHumanViolations, ReportMetadata, Violation
from constants import JIRA_ATTACHMENT_MAX_SIZE, JIRA_DESCRIPTION_MAX_CHARS, JIRA_VIOLATION_TABLE_MAX_ROWS

logger = logging.getLogger(__name__)


class ViolationFormatter:
    """Service for formatting violations into human-readable descriptions."""

    def __init__(self):
        self.logger = logger

    def _truncate_content(self, content: str, max_chars: int = JIRA_DESCRIPTION_MAX_CHARS) -> str:
        """Truncate content to fit within Jira limits."""
        if len(content) <= max_chars:
            return content

        # Truncate and add truncation notice
        truncated = content[: max_chars - 200]  # Leave room for truncation notice
        truncated += f"\n\n---\n**Content truncated due to Jira size limits. Full details available in attachment.**"

        self.logger.warning(f"Content truncated from {len(content)} to {len(truncated)} characters")
        return truncated

    def _validate_attachment_size(self, content: str) -> bool:
        """Validate attachment content size."""
        content_size = len(content.encode("utf-8"))
        if content_size > JIRA_ATTACHMENT_MAX_SIZE:
            self.logger.error(f"Attachment too large: {content_size} bytes (max: {JIRA_ATTACHMENT_MAX_SIZE})")
            return False
        return True

    def format_human_violation_description(
        self, user_group: HumanViolationGroup, report_metadata: ReportMetadata, time_period: Dict[str, str]
    ) -> str:
        """Format human violation group into Jira description."""
        description_parts = [
            "## Customer Data Access Violation",
            "",
            "### Report Overview:",
            f"**Period:** {time_period.get('start_local', 'N/A')} - {time_period.get('end_local', 'N/A')}",
            f"**User:** {user_group['user_email']}",
            f"**Violations Count:** {user_group['violations_count']}",
            "",
            "### Action Required",
            "Please provide justification for each violation in the table below.",
            "Update the justification field and save this ticket.",
            "",
            "### Violations Summary",
            "",
            "| Date | Event | Resource | Resource Details | Justification |",
            "|------|-------|----------|------------------|---------------|",
        ]

        # Add violations to table (truncated to JIRA_VIOLATION_TABLE_MAX_ROWS)
        violations_to_show = user_group["violations"][:JIRA_VIOLATION_TABLE_MAX_ROWS]
        total_violations = len(user_group["violations"])

        for violation in violations_to_show:
            event_time = violation.get("event_time", "N/A")
            event_name = violation.get("event_name", "N/A")
            resource_arn = violation.get("resource_arn", "N/A")
            resource_details = self._extract_resource_details(violation)

            # Format date to show only date and time (no seconds)
            try:
                from datetime import datetime

                if event_time != "N/A":
                    dt = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
                    formatted_date = dt.strftime("%Y-%m-%d %H:%M")
                else:
                    formatted_date = "N/A"
            except:
                formatted_date = event_time

            description_parts.append(
                f"| {formatted_date} | {event_name} | {resource_arn} | {resource_details} | **<Provide your justification here>** |"
            )

        # Add truncation notice if violations were truncated
        if total_violations > JIRA_VIOLATION_TABLE_MAX_ROWS:
            truncated_count = total_violations - JIRA_VIOLATION_TABLE_MAX_ROWS
            description_parts.extend(
                [
                    "",
                    f"**Note:** Table shows first {JIRA_VIOLATION_TABLE_MAX_ROWS} violations. {truncated_count} additional violations are available in the attached JSON report.",
                    "",
                ]
            )

        description_parts.extend(
            [
                "",
                "### User Requests",
                "",
            ]
        )

        # Collect unique requests to avoid duplication using timestamp as unique key
        unique_requests = {}
        for violation in user_group["violations"]:
            if "matched_request" in violation and violation["matched_request"]:
                matched_req = violation["matched_request"]
                # Use timestamp as unique key since multiple requests can have same Jira ID
                request_timestamp = matched_req.get("request_timestamp", "N/A")
                if request_timestamp not in unique_requests:
                    unique_requests[request_timestamp] = matched_req

        # Add unique requests only
        for i, (timestamp, matched_req) in enumerate(unique_requests.items(), 1):
            description_parts.extend(
                [
                    f"#### Request {i}:",
                    f"**Jira Issue ID:** {matched_req.get('jira_issue_id', 'N/A')}",
                    f"**Justification:** {matched_req.get('justification', 'N/A')}",
                    f"**Request Timestamp:** {matched_req.get('request_timestamp', 'N/A')}",
                    f"**Duration (minutes):** {matched_req.get('duration_minutes', 'N/A')}",
                    "",
                ]
            )

        description_parts.extend(
            [
                "### Note",
                "Full violation report and evidence are attached to this ticket.",
            ]
        )

        # Join all parts and truncate if necessary
        full_description = "\n".join(description_parts)
        return self._truncate_content(full_description)

    def _extract_resource_details(self, violation: Violation) -> str:
        """Extract specific resource details from violation data."""
        resource_details = violation.get("resource_details", {})

        if not resource_details:
            return "N/A"

        # Extract specific details based on resource type
        details_parts = []

        # For RDS resources, show database name
        if "db_name" in resource_details and resource_details["db_name"]:
            details_parts.append(f"DB Name: {resource_details['db_name']}")

        # For S3 resources, show bucket and key
        bucket = resource_details.get("bucket_name") or resource_details.get("s3_bucket")
        key = resource_details.get("object_key") or resource_details.get("s3_key")

        if bucket:
            details_parts.append(f"Bucket: {bucket}")
            if key and key != "N/A":
                details_parts.append(f"Key: {key}")

        # For other resources, show any available details
        for key, value in resource_details.items():
            if key not in ["db_name", "bucket_name", "object_key", "s3_bucket", "s3_key"] and value:
                formatted_key = key.replace("_", " ").title()
                details_parts.append(f"{formatted_key}: {value}")

        return ", ".join(details_parts) if details_parts else "N/A"

    def format_non_human_violation_description(
        self, non_human_violations: NonHumanViolations, report_metadata: ReportMetadata, time_period: Dict[str, str]
    ) -> str:
        """Format non-human violations into Jira description."""
        description_parts = [
            "## Customer Data Access Violation - Service or Unknown Actor",
            "",
            "### Report Overview:",
            f"* **Generated At:** {report_metadata['generated_at']}",
            f"* **Period:** {time_period.get('start', 'N/A')} - {time_period.get('end', 'N/A')}",
            f"* **Local Period:** {time_period.get('start_local', 'N/A')} - {time_period.get('end_local', 'N/A')}",
            "",
            "### Non-Human Violations Summary:",
            f"* **Total Count:** {non_human_violations['total_count']}",
            "",
            "#### By Category:",
        ]

        for category, count in non_human_violations["by_category"].items():
            description_parts.append(f"* **{category}:** {count}")

        description_parts.extend(["", "### Note:", "See attached report for detailed violation information.", ""])

        # Join all parts and truncate if necessary
        full_description = "\n".join(description_parts)
        return self._truncate_content(full_description)

    def _format_single_violation(self, violation: Violation, index: int) -> str:
        """Format a single violation into readable text."""
        parts = [
            f"#### Violation {index}:",
            f"* **Type:** {violation['type']}",
            f"* **Severity:** {violation['severity']}",
            f"* **User:** {violation.get('user_id', 'N/A')}",
            f"* **Actor Type:** {violation['actor_type']}",
            f"* **Resource:** {violation['resource_arn']}",
            f"* **Event Time:** {violation['event_time']}",
            f"* **Event Name:** {violation['event_name']}",
            f"* **Description:** {violation['description']}",
        ]

        # Add matched request info if present
        if "matched_request" in violation and violation["matched_request"]:
            matched_req = violation["matched_request"]
            parts.extend(
                [
                    "",
                    "##### Matched Request:",
                    f"* **Jira Issue ID:** {matched_req.get('jira_issue_id', 'N/A')}",
                    f"* **Justification:** {matched_req.get('justification', 'N/A')}",
                    f"* **Request Timestamp:** {matched_req.get('request_timestamp', 'N/A')}",
                    f"* **Duration (minutes):** {matched_req.get('duration_minutes', 'N/A')}",
                ]
            )

        # Add resource details if present
        if "resource_details" in violation and violation["resource_details"]:
            resource_details = violation["resource_details"]
            parts.append("")
            parts.append("##### Resource Details:")

            for key, value in resource_details.items():
                if value is not None:
                    parts.append(f"* **{key.replace('_', ' ').title()}:** {value}")

        # Add evidence if present
        if "evidence" in violation and violation["evidence"]:
            evidence = violation["evidence"]
            parts.append("")
            parts.append("##### Evidence:")

            for key, value in evidence.items():
                if value is not None:
                    parts.append(f"* **{key.replace('_', ' ').title()}:** {value}")

        return "\n".join(parts)

    def create_violation_attachment(self, user_group: HumanViolationGroup) -> Dict[str, str]:
        """Create attachment data for user violations."""
        attachment_data = {
            "user_email": user_group["user_email"],
            "violations_count": user_group["violations_count"],
            "violations": user_group["violations"],
        }

        content = json.dumps(attachment_data, indent=2, default=str)

        # Validate attachment size
        if not self._validate_attachment_size(content):
            # If too large, create a summary instead
            summary_data = {
                "user_email": user_group["user_email"],
                "violations_count": user_group["violations_count"],
                "message": "Full violation details too large for attachment. See Jira description for details.",
                "violation_summary": [
                    {
                        "type": v.get("type"),
                        "event_time": v.get("event_time"),
                        "resource_arn": v.get("resource_arn"),
                        "description": v.get("description"),
                    }
                    for v in user_group["violations"][:10]  # Limit to first 10 violations
                ],
            }
            content = json.dumps(summary_data, indent=2, default=str)

        return {
            "filename": f"violations_{user_group['user_email'].replace('@', '_at_')}.json",
            "content": content,
        }

    def create_non_human_attachment(self, non_human_violations: NonHumanViolations) -> Dict[str, str]:
        """Create attachment data for non-human violations."""
        content = json.dumps(non_human_violations, indent=2, default=str)

        # Validate attachment size
        if not self._validate_attachment_size(content):
            # If too large, create a summary instead
            summary_data = {
                "total_count": non_human_violations["total_count"],
                "by_category": non_human_violations["by_category"],
                "message": "Full violation details too large for attachment. See Jira description for details.",
                "violation_summary": [
                    {
                        "type": v.get("type"),
                        "event_time": v.get("event_time"),
                        "resource_arn": v.get("resource_arn"),
                        "description": v.get("description"),
                    }
                    for v in non_human_violations["violations"][:10]  # Limit to first 10 violations
                ],
            }
            content = json.dumps(summary_data, indent=2, default=str)

        return {
            "filename": "non_human_violations.json",
            "content": content,
        }
