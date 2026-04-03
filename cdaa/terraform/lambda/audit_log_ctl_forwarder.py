import base64
import gzip
import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

import boto3

LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger("botocore.credentials").setLevel(logging.WARNING)


def parse_subscription(event):
    """Decode CloudWatch Logs subscription payload (gzip+base64) into raw message strings."""
    data = event.get("awslogs", {}).get("data")
    if not data:
        return []
    raw = base64.b64decode(data)
    try:
        decompressed = gzip.decompress(raw)
    except OSError:
        decompressed = raw
    payload_str = decompressed.decode("utf-8", errors="replace")
    payload = json.loads(payload_str)
    return [rec.get("message", "") for rec in payload.get("logEvents", [])]


def extract_iso_timestamp(msg: str) -> str:
    """Extract Vault/PG timestamp in UTC ISO-8601 or fallback to now."""
    m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC)", msg)
    return (
        datetime.strptime(m.group(1), LOG_TIME_FORMAT).strftime(ISO_FORMAT)
        if m
        else datetime.now().strftime(ISO_FORMAT)
    )


def normalize_event_time(ts: str | None) -> str:
    """Normalize timestamps to RFC3339 UTC seconds (YYYY-MM-DDTHH:MM:SSZ) for CloudTrail custom schema.
    - Strips fractional seconds
    - Converts timezone offsets to Z
    - Falls back to now in UTC if parsing fails
    """
    if not ts or not isinstance(ts, str):
        return datetime.now(timezone.utc).strftime(ISO_FORMAT)
    try:
        s = ts.strip()
        # If Zulu with fractional seconds, drop fraction
        if s.endswith("Z") and "T" in s:
            if "." in s:
                s = s.split(".", 1)[0] + "Z"
            return s
        # Handle timezone offsets by using fromisoformat
        # Trim fractional part to microseconds max for fromisoformat
        if "." in s:
            head, rest = s.split(".", 1)
            # keep only digits from fraction up to 6 for fromisoformat
            frac = "".join(ch for ch in rest if ch.isdigit())[:6]
            # keep any timezone suffix (e.g., +00:00)
            tz = ""
            if "+" in rest or "-" in rest:
                # find last + or - which starts tz offset
                for i in range(len(rest)):
                    if rest[i] in "+-":
                        tz = rest[i:]
                        break
            s = head + ("." + frac if frac else "") + tz
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime(ISO_FORMAT)
    except Exception:
        return datetime.now(timezone.utc).strftime(ISO_FORMAT)


# Postgres parsers - Updated to match actual RDS log format
# PostgreSQL log parsing patterns - comprehensive coverage
PG_CONN_AUTH_RE = re.compile(r"connection authorized: user=([^\s]+) database=([^\s]+)")
PG_AUTH_PEER_RE = re.compile(r"connection authenticated: identity=\"?([^\s\"]+)\"? .*?method=([^\s]+)")
PG_DISC_RE = re.compile(r"disconnection: session time: (\d+):(\d+):(\d+) user=([^\s]+) database=([^\s]+)")


def parse_postgresql_log(message: str) -> dict | None:
    """Parse PostgreSQL connection/disconnection lines forwarded by RDS.

    Updated to handle actual RDS log format:
    2025-08-29 07:45:01 UTC:10.0.0.1(45986):[unknown]@[unknown]:[3464]:LOG:  connection received: host=10.0.0.1 port=45986
    2025-08-29 07:45:01 UTC:10.0.0.1(45986):user@database:[3464]:LOG:  connection authorized: user=user database=database
    """
    event_time_iso = extract_iso_timestamp(message)

    # Try connection authorized (most reliable)
    match_conn_auth = PG_CONN_AUTH_RE.search(message)
    if match_conn_auth:
        username, database = match_conn_auth.groups()
        return {
            "type": "DbSessionConnect",
            "eventTime": event_time_iso,
            "db_username": username,
            "database": database,
        }

    # Try connection authenticated (peer/md5 auth)
    match_auth_peer = PG_AUTH_PEER_RE.search(message)
    if match_auth_peer:
        identity, auth_method = match_auth_peer.groups()
        # Extract database from message context (user@database pattern)
        db_match = re.search(r":([^:@\s]+)@([^:\s]+):", message)
        if db_match:
            username, database = db_match.groups()
            return {
                "type": "DbSessionConnect",
                "eventTime": event_time_iso,
                "db_username": username,
                "database": database,
                "auth_method": auth_method,
                "auth_identity": identity,
            }

    # Try disconnection
    match_disconnect = PG_DISC_RE.search(message)
    if match_disconnect:
        hours, minutes, seconds, username, database = match_disconnect.groups()
        session_duration_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
        try:
            disconnect_dt = datetime.strptime(event_time_iso.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")
            connect_dt = disconnect_dt - timedelta(seconds=session_duration_seconds)
            computed_connect_iso = connect_dt.strftime(ISO_FORMAT)
        except Exception as error:
            logger.warning("pg_disconnect_connect_time_compute_failed error=%s", repr(error))
            computed_connect_iso = event_time_iso
        return {
            "type": "DbSessionDisconnect",
            "eventTime": event_time_iso,
            "db_username": username,
            "database": database,
            "session_duration_seconds": session_duration_seconds,
            "computed_connect_time": computed_connect_iso,
        }

    return None


def parse_vault_audit_log(msg: str) -> dict | None:
    """Parse Vault database creds request/response for prod roles only."""
    try:
        rec = json.loads(msg)
    except Exception:
        return None
    # Expect response entries for database creds
    req = rec.get("request", {})
    resp = rec.get("response", {})
    path = req.get("path") or rec.get("path")
    if not path or not path.startswith("database/creds/"):
        return None
    # Enforce prod creds only (e.g., database/creds/prod-ro)
    if not path.startswith("database/creds/prod-"):
        return None
    if not resp:
        # Capture request events as minimal facts
        auth = rec.get("auth", {})
        return {
            "type": "VaultCredsRequest",
            "eventTime": rec.get("time") or rec.get("@timestamp") or rec.get("timestamp") or extract_iso_timestamp(msg),
            "path": path,
            "auth_display_name": auth.get("display_name"),
            "entity_id": auth.get("entity_id"),
            "client_token_accessor": auth.get("client_token_accessor"),
            "request_id": rec.get("request_id") or req.get("id") or str(uuid.uuid4()),
            "mount_type": rec.get("mount_type"),
            "mount_accessor": rec.get("mount_accessor"),
            # networking/user agent for CTL enrichment
            "remote_address": req.get("remote_address"),
            "user_agent": (req.get("headers", {}).get("user-agent", [None]) or [None])[0],
        }
    auth = rec.get("auth", {})
    username = resp.get("data", {}).get("username") or resp.get("data", {}).get("user")
    if not username:
        return None
    lease_id = None
    secret = resp.get("secret") or {}
    if isinstance(secret, dict):
        lease_id = secret.get("lease_id")
    return {
        "type": "VaultCredsIssued",
        "eventTime": rec.get("time") or rec.get("@timestamp") or rec.get("timestamp") or extract_iso_timestamp(msg),
        "path": path,
        "auth_display_name": auth.get("display_name"),
        "entity_id": auth.get("entity_id"),
        "client_token_accessor": auth.get("client_token_accessor"),
        "username": username,
        "lease_ttl_s": resp.get("lease_duration") or resp.get("ttl"),
        "request_id": rec.get("request_id") or req.get("id") or str(uuid.uuid4()),
        "response_ts": rec.get("time") or rec.get("@timestamp") or rec.get("timestamp") or extract_iso_timestamp(msg),
        "mount_type": rec.get("mount_type"),
        "mount_accessor": rec.get("mount_accessor"),
        "lease_id": lease_id,
        # networking/user agent for CTL enrichment
        "remote_address": req.get("remote_address"),
        "user_agent": (req.get("headers", {}).get("user-agent", [None]) or [None])[0],
    }


def uuid5_hash_sensitive(value: str | None) -> str | None:
    """Pseudonymize sensitive identifiers using uuid5 (namespaced hashing)."""
    if not value:
        return value
    return f"uuid5:{uuid.uuid5(uuid.NAMESPACE_OID, value).hex}"


def get_recipient_account_id_from_channel() -> str | None:
    """Derive recipientAccountId from CTL channel ARN (arn:...:account-id:resource)."""
    # Fail-fast: no defaults for env usage
    arn = os.environ["CTL_CHANNEL_ARN"]
    parts = arn.split(":", 5)
    if len(parts) >= 5 and parts[4]:
        return parts[4]
    return None


def log_emitted_event_summary(ev: dict) -> None:
    """Emit concise, safe summaries for observability (usernames masked)."""

    def _mask_str(val: str | None, keep: int = 24) -> str | None:
        if not val:
            return val
        return val if len(val) <= keep else f"{val[:keep]}..."

    ev_type = ev.get("type") or ev.get("eventName")
    if ev_type in ("DbSessionConnect", "DbSessionDisconnect"):
        op = "connect" if ev_type.endswith("Connect") else "disconnect"
        logger.info(
            "emit_event db op=%s user=%s database=%s ts=%s",
            op,
            _mask_str(ev.get("db_username") or ev.get("auth_identity") or ev.get("username") or ev.get("user")),
            ev.get("database"),
            ev.get("eventTime"),
        )
    elif ev_type == "VaultCredsIssued":
        logger.info(
            "emit_event vault path=%s username=%s ts=%s",
            ev.get("path"),
            _mask_str(ev.get("username")),
            ev.get("eventTime"),
        )
    elif ev_type == "VaultCredsRequest":
        logger.info(
            "emit_event vault_request path=%s requester=%s ts=%s",
            ev.get("path"),
            _mask_str(ev.get("auth_display_name")),
            ev.get("eventTime"),
        )


def send_to_cloudtrail_lake(audit_events: list[dict]) -> None:
    """Send curated events to CloudTrail Lake via cloudtrail-data PutAuditEvents.
    - Fails the invocation if any event is rejected.
    - Strictly adheres to the custom audit event schema: minimal top-level fields.
    """
    if not audit_events:
        return
    client = boto3.client("cloudtrail-data")
    # Fail-fast: no defaults for env usage
    channel = os.environ["CTL_CHANNEL_ARN"]
    # Use the working userIdentity structure from 21.08.2025
    recipient_account_id = get_recipient_account_id_from_channel()

    # De-duplicate events by a stable key to respect the PutAuditEvents 100-item limit and avoid duplicates
    # Key: (type, eventTime, database|path, user)
    deduplication_keys = set()
    entries = []
    for ev in audit_events:
        key = (
            ev.get("type") or ev.get("eventName"),
            normalize_event_time(ev.get("eventTime")),
            ev.get("database") or ev.get("path") or ev.get("resource") or "",
            ev.get("db_username")
            or ev.get("username")
            or ev.get("user")
            or ev.get("auth_display_name")
            or ev.get("auth_identity")
            or "",
        )
        if key in deduplication_keys:
            continue
        deduplication_keys.add(key)
        detail = ev.copy()
        if detail.get("client_token_accessor"):
            detail["client_token_accessor"] = uuid5_hash_sensitive(detail["client_token_accessor"])
        # Remove fields not supported in CloudTrail Lake custom audit event schema
        # CloudTrail Lake custom events have strict schema validation - only specific top-level fields are allowed
        for unsupported_field in ("sourceIpAddress", "sourceipaddress", "client_addr", "source_ip"):
            detail.pop(unsupported_field, None)
        event_time = normalize_event_time(detail.get("eventTime"))
        event_name = detail.get("eventName") or detail.get("type") or "Unknown"
        event_source = detail.get("eventSource") or "audit.prod"

        # Choose a concise principal for CTL userIdentity.principalId
        # - DB events: prefer db_username (actual Postgres actor)
        # - Peer-auth (local): use auth_identity
        # - Vault events: prefer auth_display_name (often 'oidc-<email>'), fallback entity_id
        ev_type = detail.get("type") or detail.get("eventName")
        user_principal = "unknown"
        if ev_type in ("DbSessionConnect", "DbSessionDisconnect"):
            user_principal = detail.get("db_username") or detail.get("auth_identity") or "unknown"
        elif ev_type in ("VaultCredsIssued", "VaultCredsRequest"):
            user_principal = detail.get("auth_display_name") or detail.get("entity_id") or "unknown"

        user_identity = {"type": "Unknown", "principalId": str(user_principal)}

        payload = {
            "eventTime": event_time,
            "eventSource": event_source,
            "eventName": event_name,
            "userIdentity": user_identity,
            # CloudTrail custom schema requires recipientAccountId
            "recipientAccountId": recipient_account_id if recipient_account_id else None,
            "additionalEventData": detail,
        }
        logger.info("ctl_payload_keys=%s", list(payload.keys()))
        # Enrich top-level network metadata when available to avoid nulls in CTL UI
        # CloudTrail Lake custom audit events only support specific top-level fields (eventTime, eventSource, etc.)
        # Network metadata must be in additionalEventData, not as top-level sourceIpAddress
        user_agent = detail.get("user_agent")
        if user_agent:
            payload["userAgent"] = user_agent
        # Remove None values that may violate schema
        if payload.get("recipientAccountId") is None:
            del payload["recipientAccountId"]
        data_str = json.dumps(payload)
        event_id = str(uuid.uuid4())
        entries.append({"id": event_id, "eventData": data_str})
    logger.info("put_audit_events: attempting=%d (after_dedup)", len(entries))
    # CloudTrail Lake Data API limit: max 100 events per call
    total_success = 0
    total_failed = 0
    for i in range(0, len(entries), 100):
        chunk = entries[i : i + 100]
        res = client.put_audit_events(channelArn=channel, auditEvents=chunk)
        successful = res.get("successful") or []
        failed = res.get("failed") or []
        total_success += len(successful)
        total_failed += len(failed)
        if failed:
            logger.error("put_audit_events: chunk_failed=%s", json.dumps(failed))
    logger.info("put_audit_events: total_accepted=%d total_failed=%d", total_success, total_failed)
    if total_failed:
        raise RuntimeError(f"PutAuditEvents failed for {total_failed} event(s)")


def handler(event, _):
    # Log incoming event keys for diagnostics (avoid dumping full payload)
    try:
        logger.info("incoming_event keys=%s", list(event.keys())[:20])
    except Exception:
        logger.info("incoming_event received (unserializable)")

    msgs = parse_subscription(event)
    # Fail-fast: no defaults for env usage
    db_filter_str = os.environ["DATABASE_FILTER"]
    db_filter = set([x.strip() for x in db_filter_str.split(",") if x.strip()])
    out = []
    parsed = 0
    for m in msgs:
        parsed += 1
        ev = parse_postgresql_log(m)
        if not ev:
            ev = parse_vault_audit_log(m)
        if not ev:
            logger.info("skip_unparsed message - not supported")
            continue
        if ev.get("type") in ("DbSessionConnect", "DbSessionDisconnect"):
            if db_filter and ev.get("database") not in db_filter:
                logger.info("skip_db_not_in_filter database=%s", ev.get("database"))
                continue
        log_emitted_event_summary(ev)
        out.append(ev)
    logger.info("parsed_messages=%d emitted_events=%d", parsed, len(out))
    send_to_cloudtrail_lake(out)
    return {"statusCode": 200, "body": json.dumps({"emitted": len(out)})}
