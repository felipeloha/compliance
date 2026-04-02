#!/usr/bin/env python3
"""
Type definitions for Customer Data Access Audit (CDAA) system.

This module provides TypedDict definitions for better type safety and code clarity.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict


class ViolationEvidence(TypedDict, total=False):
    """Evidence data collected for a violation."""

    user_email: Optional[str]
    principal_id: Optional[str]
    session_issuer: Optional[str]
    iam_user: Optional[str]
    user_identity_type: Optional[str]
    user_identity_arn: Optional[str]
    db_username: Optional[str]
    db_auth_method: Optional[str]
    db_auth_identity: Optional[str]
    vault_auth_name: Optional[str]
    vault_lease_id: Optional[str]
    s3_request_id: Optional[str]
    s3_error_code: Optional[str]
    s3_error_message: Optional[str]
    source_ip: Optional[str]
    user_agent: Optional[str]
    aws_region: Optional[str]
    access_key_id: Optional[str]
    event_id: Optional[str]
    recipient_account_id: Optional[str]


class ResourceDetails(TypedDict, total=False):
    """Resource-specific details for a violation."""

    db_name: Optional[str]
    s3_bucket: Optional[str]
    s3_key: Optional[str]
    operation: Optional[str]


class MatchedRequest(TypedDict, total=False):
    """Matched access request details for ACCESS_OUTSIDE_WINDOW violations."""

    jira_issue_id: Optional[str]
    justification: Optional[str]
    request_timestamp: Optional[str]
    duration_minutes: Optional[int]


class Violation(TypedDict, total=False):
    """Individual violation record."""

    type: str
    severity: str
    user_id: Optional[str]
    actor_type: str
    resource_arn: str
    event_time: str
    event_name: str
    description: str
    resource_details: Optional[ResourceDetails]
    evidence: Optional[ViolationEvidence]
    matched_request: Optional[MatchedRequest]


class HumanViolationGroup(TypedDict):
    """Grouped violations for a human user."""

    user_email: str
    violations_count: int
    violations: List[Violation]


class NonHumanViolations(TypedDict):
    """Non-human violations grouped by category."""

    total_count: int
    by_category: Dict[str, int]
    violations: List[Violation]


class ViolationsGrouped(TypedDict):
    """Grouped violations structure."""

    human_violations: List[HumanViolationGroup]
    non_human_violations: NonHumanViolations


class ReportMetadata(TypedDict):
    """Report generation metadata."""

    generated_at: str
    execution_duration_seconds: float


class TimePeriod(TypedDict):
    """Time period information."""

    start: str
    end: str
    start_local: str
    end_local: str


class ExecutionSummary(TypedDict):
    """Execution summary statistics."""

    events_processed: int
    access_requests_found: int
    total_violations_found: int


class ViolationsByCategory(TypedDict):
    """Violations grouped by category."""

    s3_unauthorized_access: int
    s3_outside_window: int
    db_unauthorized_access: int
    db_outside_window: int


class ViolationsByActorType(TypedDict):
    """Violations grouped by actor type."""

    human_actors: int
    service_principals: int
    service_accounts: int
    aws_services: int
    unknown_actors: int


class AuditReport(TypedDict):
    """Complete audit report structure."""

    report_metadata: ReportMetadata
    time_period: TimePeriod
    execution_summary: ExecutionSummary
    violations_by_category: ViolationsByCategory
    violations_by_actor_type: ViolationsByActorType
    violations_grouped: ViolationsGrouped


class JiraTicketData(TypedDict):
    """Data structure for Jira ticket creation."""

    project_key: str
    issue_type: str
    summary: str
    description: str
    assignee: Optional[str]
    labels: List[str]
    attachments: Optional[List[Dict[str, str]]]


class CustomerDataConfig(TypedDict, total=False):
    """Customer data configuration structure."""

    s3_buckets: List[str]
    rds_databases: List[str]
    s3_prefixes: List[str]
    db_arn_map: Dict[str, str]


class WhitelistConfig(TypedDict, total=False):
    """Whitelist configuration structure."""

    SERVICE_PRINCIPAL: List[str]
    SERVICE_ACCOUNT: List[str]
    AWS_SERVICE: List[str]
