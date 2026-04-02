#!/usr/bin/env python3
"""
Constants for Customer Data Access Audit (CDAA) system.
"""

# Jira Configuration
JIRA_LABELS = ["audit", "cdaa", "violation"]
JIRA_ISSUE_TYPE = "Task"

# Jira Content Limits
JIRA_DESCRIPTION_MAX_CHARS = 32000  # Leave some buffer for ADF formatting below 32,767 limit
JIRA_ATTACHMENT_MAX_SIZE = 100 * 1024 * 1024  # 100MB limit
JIRA_VIOLATION_TABLE_MAX_ROWS = 20  # Maximum violations to show in table before truncation

# Violation Severity Levels
VIOLATION_SEVERITY_HIGH = "HIGH"
VIOLATION_SEVERITY_MEDIUM = "MEDIUM"

# Actor Type Constants
ACTOR_TYPE_HUMAN = "HUMAN"
ACTOR_TYPE_SERVICE_PRINCIPAL = "SERVICE_PRINCIPAL"
ACTOR_TYPE_SERVICE_ACCOUNT = "SERVICE_ACCOUNT"
ACTOR_TYPE_AWS_SERVICE = "AWS_SERVICE"
ACTOR_TYPE_UNKNOWN = "UNKNOWN"

# CloudTrail Lake Configuration
MAX_QUERY_WAIT_TIME = 840  # Align with Lambda timeout
QUERY_STATUS_CHECK_INTERVAL = 10  # Check query status every 10 seconds

# Violation Types
VIOLATION_TYPE_UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
VIOLATION_TYPE_ACCESS_OUTSIDE_WINDOW = "ACCESS_OUTSIDE_WINDOW"

# Event Names
EVENT_NAME_GET_OBJECT = "GetObject"
EVENT_NAME_PUT_OBJECT = "PutObject"
EVENT_NAME_DELETE_OBJECT = "DeleteObject"
EVENT_NAME_RESTORE_OBJECT = "RestoreObject"
EVENT_NAME_DB_SESSION_CONNECT = "DbSessionConnect"
EVENT_NAME_DB_SESSION_DISCONNECT = "DbSessionDisconnect"
EVENT_NAME_VAULT_CREDS_ISSUED = "VaultCredsIssued"

# Event Sources
EVENT_SOURCE_S3 = "s3.amazonaws.com"

# Resource ARN Prefixes
RESOURCE_ARN_S3_PREFIX = "arn:aws:s3:::"
RESOURCE_ARN_RDS_PREFIX = "arn:aws:rds:"
RESOURCE_ARN_DB_PREFIX = "db:"

# Service Role Patterns for Actor Classification
SERVICE_ROLE_PATTERNS = ["metadata-handler", "k8s-irsa-", "aws-sdk-java-", "role-"]

# Service Account Patterns
SERVICE_ACCOUNT_PATTERNS = ["role-", "k8s-irsa-", "-prod", "-service"]

# Email Regex Pattern
EMAIL_REGEX_PATTERN = r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}"

# Vault/OIDC identity prefixes (stripped when resolving email for Jira)
VAULT_OIDC_PREFIX = "v-oidc-"
OIDC_PREFIX = "oidc-"
OIDC_STRIP_PREFIXES = (VAULT_OIDC_PREFIX, OIDC_PREFIX)  # longest first

# Default Timezone
DEFAULT_TIMEZONE = "Europe/Berlin"
