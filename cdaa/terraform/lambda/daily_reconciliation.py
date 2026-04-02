#!/usr/bin/env python3
"""
Daily reconciliation for production customer data access (C5 compliance) - Refactored Version.

This is the refactored version with improved type safety, better separation of concerns,
and Jira integration capabilities.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import boto3
from audit_types import (
    AuditReport,
    CustomerDataConfig,
    ExecutionSummary,
    HumanViolationGroup,
    MatchedRequest,
    NonHumanViolations,
    ReportMetadata,
    ResourceDetails,
    TimePeriod,
    Violation,
    ViolationEvidence,
    ViolationsByActorType,
    ViolationsByCategory,
    ViolationsGrouped,
    WhitelistConfig,
)
from config import Config
from constants import (
    ACTOR_TYPE_AWS_SERVICE,
    ACTOR_TYPE_HUMAN,
    ACTOR_TYPE_SERVICE_ACCOUNT,
    ACTOR_TYPE_SERVICE_PRINCIPAL,
    ACTOR_TYPE_UNKNOWN,
    EMAIL_REGEX_PATTERN,
    EVENT_SOURCE_S3,
    MAX_QUERY_WAIT_TIME,
    OIDC_STRIP_PREFIXES,
    QUERY_STATUS_CHECK_INTERVAL,
    RESOURCE_ARN_DB_PREFIX,
    RESOURCE_ARN_RDS_PREFIX,
    RESOURCE_ARN_S3_PREFIX,
    SERVICE_ACCOUNT_PATTERNS,
    SERVICE_ROLE_PATTERNS,
    VIOLATION_SEVERITY_HIGH,
    VIOLATION_SEVERITY_MEDIUM,
    VIOLATION_TYPE_ACCESS_OUTSIDE_WINDOW,
    VIOLATION_TYPE_UNAUTHORIZED_ACCESS,
)
from services import JiraService

# Initialize AWS clients
cloudtrail = boto3.client("cloudtrail")
dynamodb = boto3.resource("dynamodb")
iam = boto3.client("iam")

logger = logging.getLogger()


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal objects."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


logger.setLevel(logging.INFO)


class DailyReconciliationService:
    """Main service for daily reconciliation processing."""

    def __init__(self):
        self.config = Config()
        self.jira_service = JiraService(self.config)
        self.logger = logger

    def process_reconciliation(self, event: Optional[Dict[str, Any]] = None) -> AuditReport:
        """Main reconciliation processing method."""
        try:
            exec_start = datetime.now(timezone.utc)

            # Calculate time window
            window_start, window_end = self._compute_time_window(event)
            self.logger.info(
                f"Starting reconciliation period start={window_start.isoformat()} end={window_end.isoformat()}"
            )

            # Query CloudTrail events
            cloudtrail_events = self._query_cloudtrail_events(window_start, window_end)

            # Get access requests
            access_requests = self._get_access_requests_for_period(window_start, window_end)
            self.logger.info(f"Retrieved {len(access_requests)} access requests")

            # Analyze violations
            violations = self._analyze_violations(access_requests, cloudtrail_events)
            self.logger.info(f"Found {len(violations)} violations")

            # Create Jira tickets - this will fail the reconciliation if Jira connector fails
            self._create_jira_tickets(violations, exec_start, window_start, window_end)

            # Build and return report
            return self._build_grouped_report(
                window_start, window_end, violations, len(cloudtrail_events), len(access_requests), exec_start
            )

        except Exception as e:
            self.logger.error(f"Daily reconciliation failed: {e}")
            raise

    def _compute_time_window(self, event: Optional[Dict[str, Any]]) -> tuple[datetime, datetime]:
        """Compute reconciliation time window."""
        now_utc = datetime.now(timezone.utc)
        start_override = (event or {}).get("start_iso") if isinstance(event, dict) else None
        end_override = (event or {}).get("end_iso") if isinstance(event, dict) else None
        period = ((event or {}).get("period") if isinstance(event, dict) else None) or "yesterday"

        # New explicit UTC args
        start_arg = (event or {}).get("start") if isinstance(event, dict) else None
        end_arg = (event or {}).get("end") if isinstance(event, dict) else None

        if start_arg and end_arg:
            window_start = datetime.fromisoformat(str(start_arg).replace("Z", "+00:00"))
            window_end = datetime.fromisoformat(str(end_arg).replace("Z", "+00:00"))
            return window_start, window_end

        if start_override and end_override:
            window_start = datetime.fromisoformat(str(start_override).replace("Z", "+00:00"))
            window_end = datetime.fromisoformat(str(end_override).replace("Z", "+00:00"))
            return window_start, window_end

        if period == "today":
            tz = ZoneInfo(self.config.reconciliation_timezone)
            now_local = now_utc.astimezone(tz)
            start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            window_start = start_local.astimezone(timezone.utc)
            return window_start, now_utc

        tz = ZoneInfo(self.config.reconciliation_timezone)
        now_local = now_utc.astimezone(tz)
        y_local = (now_local - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        y_end_local = y_local.replace(hour=23, minute=59, second=59, microsecond=999999)
        return y_local.astimezone(timezone.utc), y_end_local.astimezone(timezone.utc)

    def _query_cloudtrail_events(self, window_start: datetime, window_end: datetime) -> List[Dict[str, Any]]:
        """Query CloudTrail events for the time window."""
        # Prepare CT Lake table identifier (GUID, not ARN)
        eds_table = self._get_event_data_store_table_identifier(self.config.cloudtrail_lake_event_data_store_id)
        ts_start, ts_end = self._format_ts_literals(window_start, window_end)
        s3_filter_sql = self._build_s3_filter_sql_from_cfg()
        query_statement = self._build_s3_query(eds_table, ts_start, ts_end, s3_filter_sql)

        self.logger.info("ctl_query=%s", query_statement)

        try:
            cloudtrail_events = self._query_cloudtrail_lake(query_statement)
            self.logger.info("S3_QUERY_SUCCESS: Retrieved %d S3 events", len(cloudtrail_events))
        except Exception as e:
            self.logger.error("S3_QUERY_FAILED: %s", str(e))
            raise RuntimeError(f"S3 query failed: {e}")

        # Also query curated events (Vault/DB) if configured
        curated_events: List[Dict[str, Any]] = []
        if self.config.cloudtrail_lake_curated_store_id:
            curated_table = self._get_event_data_store_table_identifier(self.config.cloudtrail_lake_curated_store_id)
            query_curated = self._build_curated_query(curated_table, ts_start, ts_end)
            self.logger.info("ctl_query_curated=%s", query_curated)
            curated_rows = self._query_cloudtrail_lake(query_curated)
            curated_events.extend(self._process_curated_rows(curated_rows))

        s3_events_count = len(cloudtrail_events)
        cloudtrail_events.extend(curated_events)
        self.logger.info(
            f"Retrieved {len(cloudtrail_events)} CloudTrail events (S3: {s3_events_count}, Curated: {len(curated_events)})"
        )

        return cloudtrail_events

    def _get_access_requests_for_period(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Retrieve access requests for the specified time period."""
        table = dynamodb.Table(self.config.dynamodb_table_name)

        def fmt(dt: datetime) -> str:
            return dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        items: List[Dict[str, Any]] = []
        try:
            # Query per-day partition using date_berlin and timestamp range on new GSI
            tz = ZoneInfo(self.config.reconciliation_timezone)
            date_str = start_time.astimezone(tz).strftime("%Y-%m-%d")
            resp = table.query(
                IndexName="local-date-timestamp-index",
                KeyConditionExpression="#d = :d AND #ts >= :start",
                ExpressionAttributeNames={"#d": "local_date", "#ts": "timestamp"},
                ExpressionAttributeValues={":d": date_str, ":start": fmt(start_time)},
                ScanIndexForward=False,
            )
            items.extend(resp.get("Items", []))
            while resp.get("LastEvaluatedKey"):
                resp = table.query(
                    IndexName="local-date-timestamp-index",
                    KeyConditionExpression="#d = :d AND #ts >= :start",
                    ExpressionAttributeNames={"#d": "local_date", "#ts": "timestamp"},
                    ExpressionAttributeValues={":d": date_str, ":start": fmt(start_time)},
                    ExclusiveStartKey=resp["LastEvaluatedKey"],
                    ScanIndexForward=False,
                )
                items.extend(resp.get("Items", []))

            # Filter by end_time in Python
            end_time_str = fmt(end_time)
            filtered_items = [item for item in items if item.get("timestamp", "") <= end_time_str]
            return filtered_items
        except Exception as e:
            self.logger.error(f"DynamoDB per-day GSI query failed, falling back to scan: {e}")
            try:
                resp = table.scan(
                    FilterExpression="#ts BETWEEN :start AND :end",
                    ExpressionAttributeNames={"#ts": "timestamp"},
                    ExpressionAttributeValues={":start": fmt(start_time), ":end": fmt(end_time)},
                )
                items.extend(resp.get("Items", []))
                while resp.get("LastEvaluatedKey"):
                    resp = table.scan(
                        FilterExpression="#ts BETWEEN :start AND :end",
                        ExpressionAttributeNames={"#ts": "timestamp"},
                        ExpressionAttributeValues={":start": fmt(start_time), ":end": fmt(end_time)},
                        ExclusiveStartKey=resp["LastEvaluatedKey"],
                    )
                    items.extend(resp.get("Items", []))
            except Exception as ee:
                self.logger.error(f"Failed to retrieve access requests via scan: {ee}")
            return items

    def _group_violations(self, violations: List[Violation]) -> tuple[List[HumanViolationGroup], NonHumanViolations]:
        """Group violations into human and non-human categories."""
        from collections import defaultdict

        human_group: Dict[str, List[Violation]] = defaultdict(list)
        non_human_list: List[Violation] = []

        for violation in violations:
            actor_type = violation.get("actor_type", "")
            user_id = violation.get("user_id")

            if actor_type == ACTOR_TYPE_HUMAN and user_id:
                human_group[user_id].append(violation)
            else:
                non_human_list.append(violation)

        # Build human groups
        human_groups: List[HumanViolationGroup] = []
        for email, items in sorted(human_group.items(), key=lambda x: (-len(x[1]), x[0])):
            human_groups.append(HumanViolationGroup(user_email=email, violations_count=len(items), violations=items))

        # Build non-human violations
        actor_counts: Dict[str, int] = defaultdict(int)
        for violation in non_human_list:
            actor_type = violation.get("actor_type", ACTOR_TYPE_UNKNOWN)
            actor_counts[actor_type] += 1

        non_human_violations = NonHumanViolations(
            total_count=len(non_human_list),
            by_category={
                ACTOR_TYPE_SERVICE_PRINCIPAL: actor_counts.get(ACTOR_TYPE_SERVICE_PRINCIPAL, 0),
                ACTOR_TYPE_AWS_SERVICE: actor_counts.get(ACTOR_TYPE_AWS_SERVICE, 0),
                ACTOR_TYPE_UNKNOWN: actor_counts.get(ACTOR_TYPE_UNKNOWN, 0),
                ACTOR_TYPE_SERVICE_ACCOUNT: actor_counts.get(ACTOR_TYPE_SERVICE_ACCOUNT, 0),
            },
            violations=non_human_list,
        )

        return human_groups, non_human_violations

    # Helper methods (keeping the same logic as original)
    def _get_event_data_store_table_identifier(self, raw_identifier: str) -> str:
        """Return the CT Lake table identifier. Accepts ARN or GUID and returns GUID."""
        try:
            return str(raw_identifier).split("/")[-1]
        except Exception:
            return raw_identifier

    def _format_ts_literals(self, window_start: datetime, window_end: datetime) -> tuple[str, str]:
        """Format CloudTrail Lake TIMESTAMP literals as 'YYYY-MM-DD HH:MM:SS'."""
        return window_start.strftime("%Y-%m-%d %H:%M:%S"), window_end.strftime("%Y-%m-%d %H:%M:%S")

    def _build_s3_filter_sql_from_cfg(self) -> str:
        """Build S3 filters using requestParameters plus SQL-side actor whitelisting."""
        resource_predicates: List[str] = []
        actor_predicates: List[str] = []

        try:
            cfg = self.config.get_customer_data_config()
            buckets: List[str] = []
            for bucket in cfg.get("s3_buckets") or []:
                bname = str(bucket).split(":::")[-1]
                bname = bname.split("/")[0]
                if bname:
                    buckets.append(bname)
            if buckets:
                in_list = ",".join([f"'{b}'" for b in buckets])
                resource_predicates.append(f"element_at(requestParameters,'bucketName') IN ({in_list})")

            for prefix in cfg.get("s3_prefixes") or []:
                if not isinstance(prefix, str):
                    continue
                if "/" in prefix:
                    b, p = prefix.split("/", 1)
                    b = b.strip()
                    p = p.strip()
                    if b and p:
                        resource_predicates.append(
                            f"(element_at(requestParameters,'bucketName') = '{b}' AND element_at(requestParameters,'key') LIKE '{p}%')"
                        )
                else:
                    b = prefix.strip()
                    if b:
                        resource_predicates.append(f"element_at(requestParameters,'bucketName') = '{b}'")

            # Actor whitelist pushdown
            wl = self.config.get_whitelist_s3_actors()
            if wl:
                sp = [p for p in wl.get(ACTOR_TYPE_SERVICE_PRINCIPAL, []) if isinstance(p, str) and p]
                sa = [p for p in wl.get(ACTOR_TYPE_SERVICE_ACCOUNT, []) if isinstance(p, str) and p]
                aws = [p for p in wl.get(ACTOR_TYPE_AWS_SERVICE, []) if isinstance(p, str) and p]

                if sp:
                    in_list = ",".join([f"'{p}'" for p in sp])
                    actor_predicates.append(
                        f"(userIdentity.sessionContext.sessionIssuer.userName IS NULL OR lower(userIdentity.sessionContext.sessionIssuer.userName) NOT IN ({in_list}))"
                    )
                if sa:
                    in_list = ",".join([f"'{p}'" for p in sa])
                    actor_predicates.append(
                        f"(userIdentity.userName IS NULL OR lower(userIdentity.userName) NOT IN ({in_list}))"
                    )
                for substr in aws:
                    actor_predicates.append(f"(userAgent IS NULL OR lower(userAgent) NOT LIKE '%{substr}%')")
        except Exception:
            # On any config issue, skip adding filters rather than breaking the query
            pass

        clauses: List[str] = []
        if resource_predicates:
            clauses.append("(" + " OR ".join(resource_predicates) + ")")
        if actor_predicates:
            clauses.append("(" + " AND ".join(actor_predicates) + ")")
        return (" AND " + " AND ".join(clauses)) if clauses else ""

    def _build_s3_query(self, eds_table: str, ts_start: str, ts_end: str, s3_filter_sql: str) -> str:
        return f"""
            SELECT eventTime,
                   eventName,
                   eventSource,
                   awsRegion,
                   sourceIpAddress,
                   userAgent,
                   userIdentity.type AS userIdentityType,
                   userIdentity.principalId AS principalId,
                   userIdentity.arn  AS userIdentityArn,
                   userIdentity.sessionContext.sessionIssuer.userName AS sessionIssuerUserName,
                   recipientAccountId,
                   requestID,
                   element_at(requestParameters, 'bucketName') AS reqBucketName,
                   element_at(requestParameters, 'key')        AS reqObjectKey
            FROM {eds_table}
            WHERE eventTime >= TIMESTAMP '{ts_start}'
            AND eventTime <= TIMESTAMP '{ts_end}'
            AND eventSource = 's3.amazonaws.com'
            AND eventName IN ('GetObject','PutObject','DeleteObject','RestoreObject')
            {s3_filter_sql}
            ORDER BY eventTime DESC
            """

    def _build_curated_query(self, curated_table: str, ts_start: str, ts_end: str) -> str:
        return f"""
                SELECT eventTime,
                       eventData.eventName AS eventName,
                       element_at(eventData.additionalEventData, 'auth_display_name') AS auth_display_name,
                       coalesce(
                           element_at(eventData.additionalEventData,'db_username'),
                           element_at(eventData.additionalEventData,'username'),
                           element_at(eventData.additionalEventData,'user')
                       ) AS db_username,
                       element_at(eventData.additionalEventData,'database') AS database,
                       element_at(eventData.additionalEventData,'path')     AS path,
                       element_at(eventData.additionalEventData,'lease_id') AS lease_id,
                       coalesce(
                                element_at(eventData.additionalEventData,'remote_address'),
                                element_at(eventData.additionalEventData,'client_addr')
                       ) AS sourceIpAddress,
                       element_at(eventData.additionalEventData,'user_agent') AS userAgent
                FROM {curated_table}
                WHERE eventTime >= TIMESTAMP '{ts_start}'
                AND eventTime <= TIMESTAMP '{ts_end}'
                AND eventData.eventName IN ('VaultCredsIssued','DbSessionConnect','DbSessionDisconnect')
                ORDER BY eventTime DESC
                """

    def _query_cloudtrail_lake(
        self, query_statement: str, max_wait_time: int = MAX_QUERY_WAIT_TIME
    ) -> List[Dict[str, Any]]:
        """Execute CloudTrail Lake query with timeout and return list of event dicts."""
        try:
            # Start query
            response = cloudtrail.start_query(QueryStatement=query_statement)
            query_id = response["QueryId"]
            self.logger.info(f"Started CloudTrail Lake query: {query_id}")

            # Wait for completion with timeout
            start_time = datetime.now(timezone.utc)
            while True:
                if (datetime.now(timezone.utc) - start_time).total_seconds() > max_wait_time:
                    raise TimeoutError(f"Query {query_id} did not complete within {max_wait_time} seconds")

                status_response = cloudtrail.get_query_results(QueryId=query_id)
                status = status_response["QueryStatus"]

                if status == "FINISHED":
                    self.logger.info(f"Query {query_id} completed successfully")
                    # Stream-flatten rows page by page
                    events: List[Dict[str, Any]] = []
                    page_index = 1

                    def flatten_rows(rows: List[Any]) -> None:
                        for row in rows:
                            flattened_event: Dict[str, Any] = {}
                            if isinstance(row, list):
                                for cell in row:
                                    if isinstance(cell, dict):
                                        for original_key, cell_value in cell.items():
                                            key_str = str(original_key)
                                            flattened_event[key_str] = cell_value
                            events.append(flattened_event)

                    first_rows = status_response.get("QueryResultRows", [])
                    flatten_rows(first_rows)
                    self.logger.info("CTL_RESULTS page=%d rows=%d total=%d", page_index, len(first_rows), len(events))

                    next_token = status_response.get("NextToken")
                    while next_token:
                        page_index += 1
                        page = cloudtrail.get_query_results(QueryId=query_id, NextToken=next_token)
                        rows = page.get("QueryResultRows", [])
                        flatten_rows(rows)
                        self.logger.info("CTL_RESULTS page=%d rows=%d total=%d", page_index, len(rows), len(events))
                        next_token = page.get("NextToken")
                    return events
                elif status in ["FAILED", "CANCELLED"]:
                    error_msg = status_response.get("ErrorMessage", "Unknown error")
                    raise RuntimeError(f"Query {query_id} failed: {error_msg}")

                # Wait before next check
                time.sleep(QUERY_STATUS_CHECK_INTERVAL)

        except Exception as e:
            self.logger.error(f"CloudTrail Lake query failed: {e}")
            raise

    def _process_curated_rows(self, curated_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Post-process curated rows: synthesize resourceArn, and enrich DB connects with issuance metadata."""
        username_to_issuance: Dict[str, Dict[str, Any]] = {}
        for ev in curated_rows:
            if str(ev.get("eventName")) == "VaultCredsIssued" and (ev.get("db_username") or ev.get("username")):
                username_key = str(ev.get("db_username") or ev.get("username")).strip().lower()
                auth = str(ev.get("auth_display_name") or "").strip().lower()
                auth = self._strip_oidc_prefixes(auth)
                # keep the latest issuance seen for the username
                username_to_issuance[username_key] = {
                    "email": auth if auth else None,
                    "lease_id": ev.get("lease_id"),
                    "sourceIpAddress": ev.get("sourceIpAddress") or ev.get("sourceipaddress"),
                    "userAgent": ev.get("userAgent") or ev.get("user_agent"),
                }

        curated_events: List[Dict[str, Any]] = []
        for ev in curated_rows:
            if ev.get("database") and not ev.get("resourceArn"):
                ev["resourceArn"] = f"db:{ev['database']}"
            if str(ev.get("eventName")) in ("DbSessionConnect", "DbSessionDisconnect") and (
                ev.get("db_username") or ev.get("username")
            ):
                db_user_raw = str(ev.get("db_username") or ev.get("username")).strip()
                key = db_user_raw.lower()
                issuance = username_to_issuance.get(key)
                if issuance:
                    if issuance.get("email"):
                        ev["human_id"] = issuance["email"]
                    # Attach issuance metadata if missing on event
                    if issuance.get("lease_id") and not ev.get("lease_id"):
                        ev["lease_id"] = issuance["lease_id"]
                    if issuance.get("sourceIpAddress") and not (ev.get("sourceIpAddress") or ev.get("sourceipaddress")):
                        ev["sourceIpAddress"] = issuance["sourceIpAddress"]
                    if issuance.get("userAgent") and not (ev.get("userAgent") or ev.get("user_agent")):
                        ev["userAgent"] = issuance["userAgent"]
            curated_events.append(ev)
        return curated_events

    def _analyze_violations(
        self, access_requests: List[Dict[str, Any]], cloudtrail_events: List[Dict[str, Any]]
    ) -> List[Violation]:
        """Analyze violations by correlating access requests with CloudTrail events."""
        violations: List[Violation] = []

        # Build Slack-derived index once (authoritative by request email)
        requests_by_user = self._build_slack_email_maps(access_requests)

        # Check each CloudTrail event against approved requests
        cfg = self.config.get_customer_data_config()
        db_user_whitelist = set(self.config.get_whitelist_db_users())
        s3_actor_whitelist = self.config.get_whitelist_s3_actors()
        seen_violation_keys = set()

        for event in cloudtrail_events:
            # Only actual access events produce violations; VaultCredsIssued is evidence only
            event_name = str(event.get("eventName") or "")
            if event_name == "VaultCredsIssued":
                continue

            user_id = event.get("human_id") or self._derive_human_identifier(event)
            if not user_id:
                for k in ("userName", "principalId", "sessionIssuerUserName"):
                    v = event.get(k)
                    if v:
                        user_id = str(v).strip().lower()
                        break

            resource_arn, resource_details = self._canonicalize_resource(event, cfg)

            if not resource_arn:
                if event.get("eventSource") == EVENT_SOURCE_S3:
                    self.logger.warning("S3_SKIPPED: %s - no resource_arn", event.get("eventName"))
                continue

            # Skip whitelisted DB usernames
            db_username_lowercase = None
            if event.get("db_username") or event.get("username"):
                db_username_lowercase = str(event.get("db_username") or event.get("username")).strip().lower()
            if db_username_lowercase and db_username_lowercase in db_user_whitelist:
                continue

            # Classify actor type first (without email) for S3 whitelist checking
            actor_type = self._classify_actor_type(event, None)
            if event.get("eventSource") == EVENT_SOURCE_S3 and actor_type in s3_actor_whitelist:
                if self._should_skip_s3_actor(event, actor_type, s3_actor_whitelist):
                    continue

            # Resolve user_email when possible (authoritative)
            resolved_email: Optional[str] = self._resolve_user_email_from_event(user_id, event)

            # Email-only matching against requests
            approved_requests: List[Dict[str, Any]] = requests_by_user.get(resolved_email, []) if resolved_email else []

            if not approved_requests:
                # No approved request found - violation
                evidence_unauth = self._build_evidence_for_event(event, resolved_email)

                violation = Violation(
                    type=VIOLATION_TYPE_UNAUTHORIZED_ACCESS,
                    severity=VIOLATION_SEVERITY_HIGH,
                    user_id=resolved_email or None,
                    actor_type=self._classify_actor_type(event, resolved_email),
                    resource_arn=resource_arn,
                    event_time=event.get("eventTime"),
                    event_name=event.get("eventName"),
                    description=f"Access to {resource_arn} without approved request",
                    resource_details=resource_details,
                    evidence=evidence_unauth,
                )

                if self._add_violation_if_new(violations, seen_violation_keys, violation):
                    violations.append(violation)
            else:
                # Check if access is within approved time window
                event_epoch = self._parse_time_to_epoch_seconds(event.get("eventTime"))
                if event_epoch is None:
                    continue

                access_within_window = False
                for req in approved_requests:
                    request_start_epoch = self._parse_time_to_epoch_seconds(req.get("timestamp"))
                    if request_start_epoch is None:
                        continue
                    request_end_epoch = request_start_epoch + 60 * int(req.get("duration_minutes", 0))
                    if request_start_epoch <= event_epoch <= request_end_epoch:
                        access_within_window = True
                        break

                if not access_within_window:
                    evidence = self._build_evidence_for_event(event, resolved_email)
                    matched_req = approved_requests[0] if approved_requests else {}

                    violation = Violation(
                        type=VIOLATION_TYPE_ACCESS_OUTSIDE_WINDOW,
                        severity=VIOLATION_SEVERITY_MEDIUM,
                        user_id=resolved_email or None,
                        actor_type=self._classify_actor_type(event, resolved_email),
                        resource_arn=resource_arn,
                        event_time=event.get("eventTime"),
                        event_name=event.get("eventName"),
                        description=f"Access to {resource_arn} outside approved time window",
                        resource_details=resource_details,
                        evidence=evidence,
                        matched_request=MatchedRequest(
                            jira_issue_id=matched_req.get("jira_issue_id"),
                            justification=matched_req.get("justification"),
                            request_timestamp=matched_req.get("timestamp") or matched_req.get("request_timestamp"),
                            duration_minutes=matched_req.get("duration_minutes"),
                        ),
                    )

                    if self._add_violation_if_new(violations, seen_violation_keys, violation):
                        violations.append(violation)

        return violations

    def _create_jira_tickets(
        self, violations: List[Violation], exec_start: datetime, window_start: datetime, window_end: datetime
    ) -> None:
        """Create Jira tickets for violations. Fails reconciliation if Jira connector fails."""
        if not violations:
            self.logger.info("No violations to report")
            return

        # Group violations
        human_groups, non_human_violations = self._group_violations(violations)

        # Create time period info
        tz = ZoneInfo(self.config.reconciliation_timezone)
        time_period = {
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
            "start_local": window_start.astimezone(tz).isoformat(),
            "end_local": window_end.astimezone(tz).isoformat(),
        }

        # Create report metadata
        report_metadata = ReportMetadata(
            generated_at=datetime.now(timezone.utc).isoformat(),
            execution_duration_seconds=round((datetime.now(timezone.utc) - exec_start).total_seconds(), 3),
        )

        # Create tickets for human violations - will raise exception on failure
        for user_group in human_groups:
            self.jira_service.create_human_violation_ticket(user_group, report_metadata, time_period)

        # Create ticket for non-human violations - will raise exception on failure
        if non_human_violations["total_count"] > 0:
            self.jira_service.create_non_human_violation_ticket(non_human_violations, report_metadata, time_period)

    def _build_slack_email_maps(self, access_requests: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Build a simple map from identifiers to access requests."""
        requests_by_user: Dict[str, List[Dict[str, Any]]] = {}
        for req in access_requests:
            identifiers: set[str] = set()
            if req.get("user_id"):
                identifiers.add(str(req["user_id"]).strip().lower())
            if req.get("user_email"):
                email = str(req["user_email"]).strip().lower()
                identifiers.add(email)
            if req.get("user_name"):
                identifiers.add(str(req["user_name"]).strip().lower())
            for ident in identifiers:
                requests_by_user.setdefault(ident, []).append(req)
        return requests_by_user

    def _classify_actor_type(self, event: Dict[str, Any], resolved_email: Optional[str]) -> str:
        """Classify actor type based on event evidence and identity patterns."""
        # Human users with resolved email
        if resolved_email:
            return ACTOR_TYPE_HUMAN

        # AWS Service identification via service domains
        source_ip = event.get("sourceIpAddress") or ""
        user_agent = event.get("userAgent") or ""
        if isinstance(source_ip, str) and ".amazonaws.com" in source_ip:
            return ACTOR_TYPE_AWS_SERVICE
        if isinstance(user_agent, str) and ".amazonaws.com" in user_agent:
            return ACTOR_TYPE_AWS_SERVICE

        # Service Principal identification via role patterns
        principal_id_value = event.get("principalId") or ""
        session_issuer = event.get("sessionIssuerUserName") or ""

        # AssumedRole with service session names (not email)
        if isinstance(principal_id_value, str) and ":" in principal_id_value:
            session_name = principal_id_value.split(":", 1)[1]
            if any(pattern in session_name for pattern in SERVICE_ROLE_PATTERNS):
                return ACTOR_TYPE_SERVICE_PRINCIPAL

        # Service role identification via session issuer
        if isinstance(session_issuer, str):
            if any(pattern in session_issuer for pattern in SERVICE_ACCOUNT_PATTERNS):
                return ACTOR_TYPE_SERVICE_PRINCIPAL

        # IAM User identification (service accounts without email)
        user_identity_type = event.get("userIdentityType") or ""
        if user_identity_type == "IAMUser":
            return ACTOR_TYPE_SERVICE_ACCOUNT

        return ACTOR_TYPE_UNKNOWN

    def _derive_human_identifier(self, event: Dict[str, Any]) -> Optional[str]:
        """Derive a stable human identifier from a CloudTrail event."""
        # Check for direct email fields first
        for email_field in ("user_email", "email", "userEmail"):
            email_value = event.get(email_field)
            if email_value and isinstance(email_value, str):
                email_str = email_value.strip().lower()
                if re.match(EMAIL_REGEX_PATTERN, email_str):
                    return email_str

        # Check top-level identity fields
        for identity_key in ("principalId", "sessionIssuerUserName", "userName", "username"):
            identity_value = event.get(identity_key)
            if identity_value:
                identity_str = str(identity_value).strip().lower()
                # Extract email if embedded
                match_email = re.search(EMAIL_REGEX_PATTERN, identity_str)
                if match_email:
                    return match_email.group(0)
                # Extract session suffix if present (for assumed roles)
                if ":" in identity_str:
                    session_part = identity_str.split(":")[-1]
                    # Check if session part contains email
                    match_email = re.search(EMAIL_REGEX_PATTERN, session_part)
                    if match_email:
                        return match_email.group(0)
                    return session_part
                return identity_str

        # Check userIdentity nested object
        user_identity = event.get("userIdentity") or {}
        if isinstance(user_identity, dict):
            for key in ("userName", "principalId", "arn"):
                if user_identity.get(key):
                    ident = user_identity[key]
                    s = str(ident).strip().lower()
                    # If an email is embedded, prefer it
                    m_email = re.search(EMAIL_REGEX_PATTERN, s)
                    if m_email:
                        return m_email.group(0)
                    # For principalId with colon session suffix, keep session part
                    if ":" in s:
                        session_part = s.split(":")[-1]
                        # Check if session part contains email
                        m_email = re.search(EMAIL_REGEX_PATTERN, session_part)
                        if m_email:
                            return m_email.group(0)
                        return session_part
                    return s
        return None

    def _canonicalize_resource(
        self, event: Dict[str, Any], cfg: CustomerDataConfig
    ) -> tuple[Optional[str], Optional[ResourceDetails]]:
        """Return a canonical resource ARN and details for reporting."""
        ev_name = str(event.get("eventName") or "").strip()
        details: ResourceDetails = {}

        # DB curated
        if ev_name in ("DbSessionConnect", "DbSessionDisconnect") and (
            event.get("database") or event.get("resourceArn", "").startswith(RESOURCE_ARN_DB_PREFIX)
        ):
            dbname = event.get("database") or str(event.get("resourceArn")).split(":", 1)[-1]
            db_arn_map = cfg.get("db_arn_map") or {}
            rds_arn = db_arn_map.get(dbname)
            if not rds_arn:
                rds_list = cfg.get("rds_databases") or []
                if isinstance(rds_list, list) and len(rds_list) == 1:
                    rds_arn = rds_list[0]
            if rds_arn:
                details = {"db_name": dbname}
                return rds_arn, details
            # Fallback to synthetic
            return event.get("resourceArn"), {"db_name": dbname}

        # S3 native
        if event.get("eventSource") == EVENT_SOURCE_S3:
            # Case A: projected resourceArn from UNNEST(resources)
            proj_arn = event.get("resourceArn") or event.get("resourcearn")
            if proj_arn and str(proj_arn).strip():
                arn = str(proj_arn).strip()
                bucket = None
                key = None
                if arn.startswith(RESOURCE_ARN_S3_PREFIX):
                    suffix = arn.split(RESOURCE_ARN_S3_PREFIX, 1)[1]
                    parts = suffix.split("/", 1)
                    bucket = parts[0]
                    key = parts[1] if len(parts) > 1 else None
                bucket_arn = f"{RESOURCE_ARN_S3_PREFIX}{bucket}" if bucket else None
                details = {"s3_bucket": bucket, "s3_key": key, "operation": event.get("eventName")}
                return bucket_arn or arn, details

            # Case B: explicit bucket/key from requestParameters projection
            req_bucket = event.get("reqBucketName") or event.get("reqbucketname")
            req_key = event.get("reqObjectKey") or event.get("reqobjectkey")
            if isinstance(req_bucket, str) and req_bucket.strip():
                bucket = req_bucket.strip()
                key = req_key.strip() if isinstance(req_key, str) and req_key.strip() else None
                bucket_arn = f"{RESOURCE_ARN_S3_PREFIX}{bucket}"
                details = {"s3_bucket": bucket, "s3_key": key, "operation": event.get("eventName")}
                return bucket_arn, details

        return event.get("resourceArn"), {}

    def _build_evidence_for_event(self, event: Dict[str, Any], resolved_email: Optional[str]) -> ViolationEvidence:
        """Collect correlated evidence fields for a violation from the event and email resolution."""
        evidence: ViolationEvidence = {}

        # Actor Identity
        evidence["user_email"] = resolved_email if resolved_email else None
        evidence["principal_id"] = str(event.get("principalId") or event.get("principalid") or "").strip() or None
        evidence["session_issuer"] = (
            str(event.get("sessionIssuerUserName") or event.get("sessionissuerusername") or "").strip() or None
        )
        evidence["iam_user"] = str(event.get("userName") or event.get("username") or "").strip() or None
        evidence["user_identity_type"] = str(event.get("userIdentityType") or "").strip() or None
        evidence["user_identity_arn"] = str(event.get("userIdentityArn") or "").strip() or None

        # DB-specific
        if event.get("eventSource") not in (EVENT_SOURCE_S3,):
            evidence["db_username"] = (
                str(event.get("db_username") or event.get("username") or event.get("user") or "").strip() or None
            )
        else:
            evidence["db_username"] = None
        evidence["db_auth_method"] = str(event.get("auth_method") or "").strip() or None
        evidence["db_auth_identity"] = str(event.get("auth_identity") or "").strip() or None

        # Vault-specific
        evidence["vault_auth_name"] = str(event.get("auth_display_name") or "").strip() or None
        evidence["vault_lease_id"] = str(event.get("lease_id") or "").strip() or None

        # S3-specific
        evidence["s3_request_id"] = str(event.get("requestID") or event.get("requestid") or "").strip() or None
        evidence["s3_error_code"] = str(event.get("errorCode") or event.get("errorcode") or "").strip() or None
        evidence["s3_error_message"] = str(event.get("errorMessage") or event.get("errormessage") or "").strip() or None

        # Network/Access Context
        source_ip = (
            event.get("sourceIpAddress")
            or event.get("sourceipaddress")
            or event.get("client_addr")
            or event.get("remote_address")
        )
        evidence["source_ip"] = str(source_ip).strip() if source_ip else None
        user_agent = event.get("userAgent")
        evidence["user_agent"] = str(user_agent).strip() if user_agent else None
        evidence["aws_region"] = str(event.get("awsRegion") or "").strip() or None
        evidence["access_key_id"] = str(event.get("accessKeyId") or "").strip() or None
        evidence["event_id"] = str(event.get("eventID") or "").strip() or None
        evidence["recipient_account_id"] = str(event.get("recipientAccountId") or "").strip() or None

        return evidence

    def _strip_oidc_prefixes(self, s: str) -> str:
        """Strip Vault/OIDC identity prefixes so Jira receives plain email."""
        for prefix in OIDC_STRIP_PREFIXES:
            if s.startswith(prefix):
                return s[len(prefix) :]
        return s

    def _resolve_user_email_from_event(
        self, raw_user_identifier: Optional[str], event: Dict[str, Any]
    ) -> Optional[str]:
        """Resolve definitive user email for correlation."""
        # Prefer event-provided human_id/auth_display_name when they contain an email
        for key in ("human_id", "auth_display_name"):
            val = event.get(key)
            if isinstance(val, str):
                s = self._strip_oidc_prefixes(val.lower().strip())
                m = re.search(EMAIL_REGEX_PATTERN, s)
                if m:
                    return m.group(0)

        # S3 AssumedRole: principalId contains the email after colon for SSO users
        if event.get("eventSource") == EVENT_SOURCE_S3:
            principal_id_value = event.get("principalId") or event.get("principalid") or ""
            if isinstance(principal_id_value, str) and ":" in principal_id_value:
                session_name_part = self._strip_oidc_prefixes(principal_id_value.split(":", 1)[1].strip().lower())
                email_match = re.search(EMAIL_REGEX_PATTERN, session_name_part)
                if email_match:
                    return email_match.group(0)
            # Check projected userName fields for direct emails as fallback
            for field_name in ("userName", "username", "sessionIssuerUserName", "sessionissuerusername"):
                field_value = event.get(field_name)
                if isinstance(field_value, str):
                    normalized = self._strip_oidc_prefixes(field_value.lower())
                    email_match = re.search(EMAIL_REGEX_PATTERN, normalized)
                    if email_match:
                        return email_match.group(0)

        # Check userIdentity nested object for email patterns
        user_identity = event.get("userIdentity") or {}
        if isinstance(user_identity, dict):
            for key in ("userName", "principalId", "arn", "type"):
                if user_identity.get(key):
                    ident = self._strip_oidc_prefixes(str(user_identity[key]).strip().lower())
                    m_email = re.search(EMAIL_REGEX_PATTERN, ident)
                    if m_email:
                        return m_email.group(0)
                    if ":" in str(user_identity[key]):
                        session_part = self._strip_oidc_prefixes(str(user_identity[key]).strip().lower().split(":")[-1])
                        m_email = re.search(EMAIL_REGEX_PATTERN, session_part)
                        if m_email:
                            return m_email.group(0)

        # RDS events: Check db_username for vault/OIDC patterns
        if event.get("eventSource") not in (EVENT_SOURCE_S3,):
            db_username = event.get("db_username") or event.get("username") or event.get("user")
            if isinstance(db_username, str) and any(db_username.startswith(p) for p in OIDC_STRIP_PREFIXES):
                # Log when we encounter Vault OIDC usernames without proper correlation
                self.logger.warning(
                    f"Vault OIDC username detected without email correlation: {db_username}. "
                    "Check if Vault credential issuance events are being processed correctly."
                )

        # IAM User email resolution from tags (for IAM users without direct email)
        user_identity_arn = event.get("userIdentityArn") or ""
        if (
            isinstance(user_identity_arn, str)
            and user_identity_arn.startswith("arn:aws:iam::")
            and ":user/" in user_identity_arn
        ):
            iam_email = self._resolve_iam_user_email_from_tags(user_identity_arn)
            if iam_email:
                return iam_email

        # Fallback: raw identifier if it is an email (strip OIDC prefix first)
        if isinstance(raw_user_identifier, str):
            normalized = self._strip_oidc_prefixes(raw_user_identifier.lower())
            m = re.search(EMAIL_REGEX_PATTERN, normalized)
            if m:
                return m.group(0)

        return None

    def _resolve_iam_user_email_from_tags(self, user_identity_arn: str) -> Optional[str]:
        """Resolve IAM user email from user tags (owner tag)."""
        try:
            if not user_identity_arn or not isinstance(user_identity_arn, str):
                return None

            # Extract username from ARN: arn:aws:iam::account:user/username
            if not user_identity_arn.startswith("arn:aws:iam::") or ":user/" not in user_identity_arn:
                return None

            username = user_identity_arn.split(":user/", 1)[1]
            if not username:
                return None

            # Get user tags
            response = iam.list_user_tags(UserName=username)
            tags = response.get("Tags", [])

            # Look for owner tag with email
            for tag in tags:
                if tag.get("Key") == "owner":
                    owner_value = tag.get("Value", "").strip()
                    if owner_value:
                        # Validate if it's an email
                        email_match = re.search(EMAIL_REGEX_PATTERN, owner_value.lower())
                        if email_match:
                            return email_match.group(0)

            self.logger.debug(f"No owner email tag found for IAM user: {username}")
            return None

        except Exception as e:
            self.logger.warning(f"Failed to resolve IAM user email from tags for {user_identity_arn}: {e}")
            return None

    def _parse_time_to_epoch_seconds(self, ts: str) -> Optional[float]:
        """Parse various CTL/ISO timestamps to epoch seconds (UTC)."""
        try:
            if not ts:
                return None
            s = str(ts).strip()
            if s.endswith("Z"):
                # ISO with Z; ensure +00:00
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                return dt.timestamp()
            # Handle space-separated TS with optional fractional seconds
            if "." in s:
                s2 = s.split(".")[0]
            else:
                s2 = s
            dt = datetime.strptime(s2, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except Exception:
            return None

    def _should_skip_s3_actor(
        self, event: Dict[str, Any], actor_type: str, s3_actor_whitelist: Dict[str, List[str]]
    ) -> bool:
        """Check if S3 actor should be skipped based on whitelist."""
        patterns = s3_actor_whitelist.get(actor_type, [])

        if actor_type == ACTOR_TYPE_SERVICE_PRINCIPAL:
            # PRIMARY: Check session_issuer (most reliable for k8s-irsa roles)
            session_issuer = event.get("sessionIssuerUserName") or event.get("sessionissuerusername") or ""
            # SECONDARY: Check principal_id session name (fallback)
            principal_id_value = event.get("principalId") or event.get("principalid") or ""
            session_name = ""
            if isinstance(principal_id_value, str) and ":" in principal_id_value:
                session_name = principal_id_value.split(":", 1)[1]
            if isinstance(session_issuer, str) and session_issuer.strip():
                if any(p == session_issuer.lower() for p in patterns):
                    return True
            if session_name and any(p == session_name.lower() for p in patterns):
                return True

        elif actor_type == ACTOR_TYPE_AWS_SERVICE:
            # Exact host match against whitelist (no wildcards)
            src = event.get("sourceIpAddress") or event.get("sourceipaddress") or ""
            ua = event.get("userAgent") or event.get("user_agent") or ""
            host = str(src).strip().lower() if isinstance(src, str) else ""
            if not host and isinstance(ua, str) and ".amazonaws.com" in ua:
                # Extract hostname token if UA contains it
                host = ua.strip().lower()
            if host and any(p == host for p in patterns):
                return True

        elif actor_type == ACTOR_TYPE_SERVICE_ACCOUNT:
            # Exact match against IAM user (iam_user) to allow bots
            iam_user = event.get("userName") or event.get("username") or event.get("iam_user") or ""
            if isinstance(iam_user, str) and iam_user.strip():
                if any(p == iam_user.strip().lower() for p in patterns):
                    return True

        return False

    def _add_violation_if_new(self, violations: List[Violation], seen_keys: set, violation: Violation) -> bool:
        """Check if violation is new and add it if so."""
        vkey = (
            violation["type"],
            violation["user_id"],
            violation["resource_arn"],
            violation.get("event_time"),
            violation.get("event_name"),
        )
        if vkey in seen_keys:
            return False
        seen_keys.add(vkey)
        return True

    def _build_grouped_report(
        self,
        window_start: datetime,
        window_end: datetime,
        violations: List[Violation],
        events_processed: int,
        access_requests_found: int,
        exec_start: datetime,
    ) -> AuditReport:
        """Build the final grouped report."""
        from collections import defaultdict

        # Category counters
        s3_unauthorized_count = 0
        s3_outside_window_count = 0
        db_unauthorized_count = 0
        db_outside_window_count = 0

        # Actor counters
        actor_counts: Dict[str, int] = defaultdict(int)

        # Groupings
        human_group: Dict[str, List[Violation]] = defaultdict(list)
        non_human_list: List[Violation] = []

        for violation in violations:
            violation_type = str(violation.get("type"))
            actor_type = str(violation.get("actor_type"))
            resource_arn = str(violation.get("resource_arn") or "")

            is_s3 = resource_arn.startswith(RESOURCE_ARN_S3_PREFIX)
            is_db = resource_arn.startswith(RESOURCE_ARN_RDS_PREFIX) or resource_arn.startswith(RESOURCE_ARN_DB_PREFIX)

            if is_s3:
                if violation_type == VIOLATION_TYPE_UNAUTHORIZED_ACCESS:
                    s3_unauthorized_count += 1
                elif violation_type == VIOLATION_TYPE_ACCESS_OUTSIDE_WINDOW:
                    s3_outside_window_count += 1
            elif is_db:
                if violation_type == VIOLATION_TYPE_UNAUTHORIZED_ACCESS:
                    db_unauthorized_count += 1
                elif violation_type == VIOLATION_TYPE_ACCESS_OUTSIDE_WINDOW:
                    db_outside_window_count += 1

            actor_counts[actor_type] += 1

            if actor_type == ACTOR_TYPE_HUMAN and violation.get("user_id"):
                human_group[str(violation["user_id"])].append(violation)
            else:
                non_human_list.append(violation)

        # Build actor type summary
        violations_by_actor_type = ViolationsByActorType(
            human_actors=actor_counts.get(ACTOR_TYPE_HUMAN, 0),
            service_principals=actor_counts.get(ACTOR_TYPE_SERVICE_PRINCIPAL, 0),
            service_accounts=actor_counts.get(ACTOR_TYPE_SERVICE_ACCOUNT, 0),
            aws_services=actor_counts.get(ACTOR_TYPE_AWS_SERVICE, 0),
            unknown_actors=actor_counts.get(ACTOR_TYPE_UNKNOWN, 0),
        )

        # Human grouped list
        human_grouped_list: List[HumanViolationGroup] = []
        for email, items in sorted(human_group.items(), key=lambda x: (-len(x[1]), x[0])):
            human_grouped_list.append(
                HumanViolationGroup(
                    user_email=email,
                    violations_count=len(items),
                    violations=items,
                )
            )

        # Non-human breakdown
        non_human_by_category = {
            ACTOR_TYPE_SERVICE_PRINCIPAL: actor_counts.get(ACTOR_TYPE_SERVICE_PRINCIPAL, 0),
            ACTOR_TYPE_AWS_SERVICE: actor_counts.get(ACTOR_TYPE_AWS_SERVICE, 0),
            ACTOR_TYPE_UNKNOWN: actor_counts.get(ACTOR_TYPE_UNKNOWN, 0),
            ACTOR_TYPE_SERVICE_ACCOUNT: actor_counts.get(ACTOR_TYPE_SERVICE_ACCOUNT, 0),
        }

        # Localized period
        tz = ZoneInfo(self.config.reconciliation_timezone)
        start_local = window_start.astimezone(tz).isoformat()
        end_local = window_end.astimezone(tz).isoformat()

        return AuditReport(
            report_metadata=ReportMetadata(
                generated_at=datetime.now(timezone.utc).isoformat(),
                execution_duration_seconds=round((datetime.now(timezone.utc) - exec_start).total_seconds(), 3),
            ),
            time_period=TimePeriod(
                start=window_start.isoformat(),
                end=window_end.isoformat(),
                start_local=start_local,
                end_local=end_local,
            ),
            execution_summary=ExecutionSummary(
                events_processed=events_processed,
                access_requests_found=access_requests_found,
                total_violations_found=len(violations),
            ),
            violations_by_category=ViolationsByCategory(
                s3_unauthorized_access=s3_unauthorized_count,
                s3_outside_window=s3_outside_window_count,
                db_unauthorized_access=db_unauthorized_count,
                db_outside_window=db_outside_window_count,
            ),
            violations_by_actor_type=violations_by_actor_type,
            violations_grouped=ViolationsGrouped(
                human_violations=human_grouped_list,
                non_human_violations=NonHumanViolations(
                    total_count=len(non_human_list),
                    by_category=non_human_by_category,
                    violations=non_human_list,
                ),
            ),
        )


def lambda_handler(event, context):
    """Main Lambda handler for daily reconciliation."""
    try:
        exec_start = datetime.now(timezone.utc)

        # Calculate time window (default: previous day). Allow ad-hoc overrides for testing.
        window_start, window_end = compute_time_window(event if isinstance(event, dict) else None)

        logger.info(f"Starting reconciliation period start={window_start.isoformat()} end={window_end.isoformat()}")

        # Initialize the service
        service = DailyReconciliationService()

        # Generate the report
        report = service.process_reconciliation(event)

        logger.info(
            f"Reconciliation completed successfully. Found {report['execution_summary']['total_violations_found']} violations."
        )

        return report

    except Exception as e:
        logger.error(f"Daily reconciliation failed: {e}")
        raise


def compute_time_window(event: Optional[Dict[str, Any]]) -> tuple[datetime, datetime]:
    """Compute the time window for reconciliation."""
    if event and "start" in event and "end" in event:
        # Ad-hoc testing override
        start_str = event["start"]
        end_str = event["end"]
        window_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        window_end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
    else:
        # Default: previous day
        now = datetime.now(timezone.utc)
        window_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        window_start = window_end - timedelta(days=1)

    return window_start, window_end
