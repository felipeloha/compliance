"""Slack Access Request Handler (KISS/DRY)

Single Lambda handles slash command and interactivity. Validates Slack
signatures, opens a minimal modal (Jira, Justification, Duration),
persists request metadata to DynamoDB, and confirms in-modal.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict
from urllib import request as urlrequest
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

import boto3

# Environment variables - fail fast if missing
SLACK_SIGNING_SECRET_PARAM_NAME = os.environ["SLACK_SIGNING_SECRET_PARAM_NAME"]
SLACK_BOT_TOKEN_PARAM_NAME = os.environ["SLACK_BOT_TOKEN_PARAM_NAME"]
DYNAMODB_TABLE_NAME = os.environ["DYNAMODB_TABLE_NAME"]
ALLOWED_DURATIONS_PARAM = os.environ["ALLOWED_DURATIONS_PARAM"]
LOCAL_TIMEZONE = os.environ["LOCAL_TIMEZONE"]
ACCESS_REQUEST_RETENTION_YEARS = int(os.environ["ACCESS_REQUEST_RETENTION_YEARS"])  # compliance retention

# Pre-resolve timezone; fail immediately if invalid
LOCAL_TZ = ZoneInfo(LOCAL_TIMEZONE)

# Initialize AWS clients
ssm = boto3.client("ssm")
dynamodb = boto3.resource("dynamodb")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SLACK_API_BASE_URL = "https://slack.com/api"
UTF8 = "utf-8"
CONTENT_TYPE_JSON = "application/json; charset=utf-8"


def verify_slack_signature(headers, body: str, signing_secret: str) -> bool:
    """Validate Slack signature, reject replayed requests (>5 minutes)."""
    ts = headers.get("x-slack-request-timestamp") or headers.get("X-Slack-Request-Timestamp")
    sig = headers.get("x-slack-signature") or headers.get("X-Slack-Signature")
    if not ts or not sig:
        return False
    # prevent replay
    if abs(time.time() - int(ts)) > 60 * 5:
        return False
    basestring = f"v0:{ts}:{body}".encode(UTF8)
    digest = hmac.new(signing_secret.encode(UTF8), basestring, hashlib.sha256).hexdigest()
    expected = f"v0={digest}"
    return hmac.compare_digest(expected, sig)


def parse_plaintext_payload(form: dict, allowed_durations: set[int]) -> tuple[int, str, str]:
    """Fallback plain-text parsing for quick testing (no modal)."""
    justification = (form.get("justification", [""])[0]).strip()
    jira_id = (form.get("jira_id", [""])[0]).strip()
    duration_str = (form.get("duration", [""])[0]).strip()

    if not justification:
        raise ValueError("Justification is required")
    if not jira_id:
        raise ValueError("Jira ID is required")
    if not re.match(r"^[A-Z][A-Z0-9]+-\d+$", jira_id):
        raise ValueError("Jira ID format invalid")
    if not duration_str:
        raise ValueError("Duration is required")
    try:
        minutes = int(duration_str)
    except Exception:
        raise ValueError("Duration must be one of: " + ", ".join(map(str, sorted(list(allowed_durations)))))
    if minutes not in allowed_durations:
        raise ValueError("Duration must be one of: " + ", ".join(map(str, sorted(list(allowed_durations)))))

    return minutes, justification, jira_id


def get_ssm_parameter(name: str, decrypt: bool = False) -> str:
    """Read SSM parameter, log on failure, re-raise to fail fast."""
    try:
        resp = ssm.get_parameter(Name=name, WithDecryption=decrypt)
        return resp["Parameter"]["Value"]
    except Exception as e:
        logger.error("ssm_get_parameter_failed name=%s decrypt=%s error=%s", name, decrypt, repr(e))
        raise


def open_slack_view(bot_token: str, trigger_id: str, view: dict) -> None:
    """Open a Slack modal using views.open."""
    try:
        data = json.dumps({"trigger_id": trigger_id, "view": view}).encode(UTF8)
        req = urlrequest.Request(
            url=f"{SLACK_API_BASE_URL}/views.open",
            data=data,
            headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {bot_token}"},
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=5) as resp:
            body = resp.read().decode(UTF8)
            logger.info("slack_views_open_response=%s", body[:400])
    except Exception as e:
        logger.error("slack_views_open_failed error=%s", repr(e))
        raise


def update_slack_view(bot_token: str, view_id: str, view: dict, view_hash: str | None = None) -> None:
    """Update an open Slack modal using views.update (for dependent selects)."""
    try:
        payload = {"view_id": view_id, "view": view}
        if view_hash:
            payload["hash"] = view_hash
        data = json.dumps(payload).encode(UTF8)
        req = urlrequest.Request(
            url=f"{SLACK_API_BASE_URL}/views.update",
            data=data,
            headers={"Content-Type": CONTENT_TYPE_JSON, "Authorization": f"Bearer {bot_token}"},
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=5) as resp:
            body = resp.read().decode(UTF8)
            logger.info("slack_views_update_response=%s", body[:400])
    except Exception as e:
        logger.error("slack_views_update_failed error=%s", repr(e))
        raise


def build_option(text: str, value: str) -> dict:
    """Build a Block Kit option object for static_select lists."""
    return {"text": {"type": "plain_text", "text": text}, "value": value}


def build_success_view(message: str) -> dict:
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Access Request"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": message}},
        ],
    }


def build_error_view(message: str) -> dict:
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Access Request"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f":warning: {message}"}},
        ],
    }


def fetch_slack_user_email(bot_token: str, user_id: str) -> str | None:
    """Fetch user's email using Slack Web API; returns email or None.

    Note:
    - Slack slash/interactive payloads DO NOT include email (privacy by design).
    - The documented way to get email is calling users.info (or users.profile.get)
      with scope users:read.email using the user's ID from the payload.
      Docs: https://api.slack.com/methods/users.info
            https://api.slack.com/scopes/users:read.email
    """
    try:
        req = urlrequest.Request(
            url=f"{SLACK_API_BASE_URL}/users.info?user={user_id}",
            headers={"Authorization": f"Bearer {bot_token}"},
            method="GET",
        )
        with urlrequest.urlopen(req, timeout=5) as resp:
            body = resp.read().decode(UTF8)
            data = json.loads(body)
            if data.get("ok") and data.get("user", {}).get("profile", {}).get("email"):
                return data["user"]["profile"]["email"]
            logger.warning("slack_users_info_no_email user=%s", user_id)
            return None
    except Exception as e:
        logger.error("slack_users_info_failed user=%s error=%s", user_id, repr(e))
        return None


def build_access_request_modal(allowed_durations: list[int]) -> dict:
    """Build minimal modal (Jira, Justification, Duration)."""
    duration_options = [build_option(f"{m} min", str(m)) for m in sorted(allowed_durations)]
    blocks: list[dict] = [
        {"type": "section", "text": {"type": "mrkdwn", "text": "Submit a temporary prod access request."}},
        {
            "type": "input",
            "block_id": "jira",
            "element": {
                "type": "plain_text_input",
                "action_id": "jira_key",
                "placeholder": {"type": "plain_text", "text": "ENG-1234"},
            },
            "label": {"type": "plain_text", "text": "Jira Ticket"},
        },
        {
            "type": "input",
            "block_id": "just",
            "element": {"type": "plain_text_input", "action_id": "justification", "multiline": True},
            "label": {"type": "plain_text", "text": "Justification"},
        },
        {
            "type": "input",
            "block_id": "duration",
            "element": {"type": "static_select", "action_id": "duration_select", "options": duration_options},
            "label": {"type": "plain_text", "text": "Duration"},
        },
    ]

    return {
        "type": "modal",
        "callback_id": "access_request",
        "title": {"type": "plain_text", "text": "Access Request"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": blocks,
    }


def lambda_handler(event, context):
    try:
        # HTTP API v2 payload
        raw_body = event.get("body", "") or ""
        is_b64 = bool(event.get("isBase64Encoded"))
        if is_b64 and raw_body:
            try:
                raw_body = base64.b64decode(raw_body).decode(UTF8)
            except Exception as e:
                logger.error("body_base64_decode_failed error=%s", repr(e))
                raw_body = ""
        headers = event.get("headers", {}) or {}
        logger.info(
            "incoming_request context=%s",
            json.dumps(
                {
                    "has_body": bool(raw_body),
                    "header_keys": list(headers.keys())[:10],
                    "is_base64": is_b64,
                    "body_len": len(raw_body),
                    "body_sha256_prefix": hashlib.sha256(raw_body.encode(UTF8)).hexdigest()[:8] if raw_body else None,
                }
            ),
        )

        # Log Slack signature header presence and abbreviated values for RCA
        ts_hdr = headers.get("x-slack-request-timestamp") or headers.get("X-Slack-Request-Timestamp")
        sig_hdr = headers.get("x-slack-signature") or headers.get("X-Slack-Signature")
        logger.info(
            "slack_sig_header_presence context=%s",
            json.dumps(
                {
                    "has_ts": bool(ts_hdr),
                    "has_sig": bool(sig_hdr),
                    "ts": ts_hdr,
                    "sig_prefix": (sig_hdr[:6] if sig_hdr else None),
                }
            ),
        )

        # Retrieve Slack signing secret
        secret = ssm.get_parameter(Name=SLACK_SIGNING_SECRET_PARAM_NAME, WithDecryption=True)["Parameter"]["Value"]

        # Compute and log expected signature prefix (non-sensitive) if timestamp present
        if ts_hdr:
            try:
                basestring = f"v0:{ts_hdr}:{raw_body}".encode(UTF8)
                digest = hmac.new(secret.encode(UTF8), basestring, hashlib.sha256).hexdigest()
                expected = f"v0={digest}"
                logger.info("slack_sig_expected_prefix prefix=%s", expected[:8])
            except Exception as e:
                logger.error("slack_sig_expected_compute_failed error=%s", repr(e))

        if not verify_slack_signature(headers, raw_body, secret):
            logger.warning("slack_signature_invalid")
            # Return 200 to avoid Slack 'dispatch_failed' banner while still logging
            return {"statusCode": 200, "body": "invalid signature"}

        # Slack sends form-encoded body
        form = parse_qs(raw_body)

        # Interactivity: view_submission from modal
        if "payload" in form:
            try:
                payload = json.loads(form["payload"][0])
            except Exception as e:
                logger.error("slack_payload_parse_failed error=%s raw=%s", repr(e), raw_body[:200])
                return {"statusCode": 400, "headers": {"Content-Type": CONTENT_TYPE_JSON}, "body": json.dumps({})}
            if (
                payload.get("type") == "view_submission"
                and payload.get("view", {}).get("callback_id") == "access_request"
            ):
                state = payload["view"].get("state", {}).get("values", {})

                def _get(block, action):
                    return ((state.get(block) or {}).get(action) or {}).get("value")

                jira_key = _get("jira", "jira_key") or ""
                justification = _get("just", "justification") or ""
                duration_val = (
                    ((state.get("duration") or {}).get("duration_select") or {}).get("selected_option") or {}
                ).get("value")
                try:
                    allowed_durations_str = get_ssm_parameter(ALLOWED_DURATIONS_PARAM, decrypt=False)
                except Exception as e:
                    logger.error("ssm_load_failed error=%s", repr(e))
                    # Inline error update so Slack shows it in the same modal
                    return {
                        "statusCode": 200,
                        "headers": {"Content-Type": CONTENT_TYPE_JSON},
                        "body": json.dumps(
                            {"response_action": "update", "view": build_error_view("Configuration could not be loaded")}
                        ),
                    }

                allowed = set(int(x) for x in allowed_durations_str.split(",") if x)
                errors = {}
                if not jira_key or not re.match(r"^[A-Z][A-Z0-9]+-\d+$", jira_key):
                    errors["jira"] = {"jira_key": "Invalid Jira key"}
                if not justification:
                    errors["just"] = {"justification": "Justification required"}
                try:
                    minutes = int(duration_val or "0")
                except Exception:
                    minutes = 0
                if minutes not in allowed:
                    errors["duration"] = {"duration_select": f"Duration must be one of: {sorted(list(allowed))}"}
                if errors:
                    return {
                        "statusCode": 200,
                        "headers": {"Content-Type": CONTENT_TYPE_JSON},
                        "body": json.dumps(
                            {"response_action": "errors", "errors": {k: list(v.values())[0] for k, v in errors.items()}}
                        ),
                    }

                table = dynamodb.Table(DYNAMODB_TABLE_NAME)
                now_epoch = int(time.time())
                now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_epoch))
                expiry_epoch = now_epoch + minutes * 60
                expiry_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expiry_epoch))
                # Local date (partition for GSI)
                local_date = datetime.now(tz=LOCAL_TZ).date().isoformat()
                # TTL based on retention policy (years), not access window
                retention_ttl_epoch = now_epoch + ACCESS_REQUEST_RETENTION_YEARS * 365 * 24 * 3600

                user = payload.get("user", {})
                user_id = user.get("id") or "unknown"
                user_name = user.get("username") or user.get("name") or "unknown"
                # Resolve real email via Slack API.
                # Slack does not include email in slash/interactive payloads;
                # we must call users.info (users:read.email) to retrieve it.
                try:
                    bot_token = get_ssm_parameter(SLACK_BOT_TOKEN_PARAM_NAME, decrypt=True)
                    resolved_email = fetch_slack_user_email(bot_token, user_id)
                    if not resolved_email:
                        raise ValueError("email_not_returned")
                except Exception as e:
                    logger.error("slack_email_resolution_failed user=%s error=%s", user_id, repr(e))
                    return {
                        "statusCode": 200,
                        "headers": {"Content-Type": CONTENT_TYPE_JSON},
                        "body": json.dumps(
                            {
                                "response_action": "update",
                                "view": build_error_view(
                                    "Unable to resolve your email from Slack (users.info). Please retry or contact admins."
                                ),
                            }
                        ),
                    }

                item = {
                    "request_id": str(uuid.uuid4()),
                    "timestamp": now_iso,
                    "local_date": local_date,
                    "user_id": user_id,
                    "user_name": user_name,
                    "user_email": resolved_email,
                    "jira_issue_id": jira_key,
                    "justification": justification,
                    "duration_minutes": minutes,
                    "request_timestamp": now_iso,
                    "expiry_timestamp": expiry_iso,
                    "ttl": retention_ttl_epoch,
                }
                table.put_item(Item=item)
                logger.info(
                    "slack_request_persisted context=%s",
                    json.dumps({"request_id": item["request_id"], "user": user_name, "minutes": minutes}),
                )
                # Inline update of the modal with success confirmation (no notification claim)
                success_text = f"Request submitted successfully.\nRequest ID: {item['request_id']}"
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": CONTENT_TYPE_JSON},
                    "body": json.dumps({"response_action": "update", "view": build_success_view(success_text)}),
                }

        # Slash command: open modal
        if form.get("command", [""])[0] == "/request-customer-data-access" and form.get("trigger_id", [""])[0]:
            try:
                bot_token = get_ssm_parameter(SLACK_BOT_TOKEN_PARAM_NAME, decrypt=True)
                allowed_durations_str = get_ssm_parameter(ALLOWED_DURATIONS_PARAM, decrypt=False)
                durations = sorted([int(x) for x in allowed_durations_str.split(",") if x.strip()])
                view = build_access_request_modal(durations)
                open_slack_view(bot_token, form["trigger_id"][0], view)
                return {"statusCode": 200, "body": "Opening access request form…"}
            except Exception as e:
                logger.error("slash_modal_open_failed error=%s", repr(e))
                # fall through to plain-text mode

        user_id = form.get("user_id", ["unknown"])[0]
        user_name = form.get("user_name", ["unknown"])[0]
        text = form.get("text", [""])[0]

        # Strict: no defaults; fail fast if required config is missing
        allowed_durations_str = get_ssm_parameter(ALLOWED_DURATIONS_PARAM, decrypt=False)

        # Minimal plaintext support: text format "JIRA-123 Justification;30"
        # If not present, respond with guidance
        try:
            parts = text.split(";", 1)
            left = (parts[0] if parts else "").strip()
            minutes = int((parts[1] if len(parts) > 1 else "0").strip()) if ";" in text else 0
            if " " in left:
                jira_id = left.split(" ", 1)[0].strip()
                justification = left.split(" ", 1)[1].strip()
            else:
                jira_id = left
                justification = ""
        except Exception:
            jira_id, justification, minutes = "", "", 0

        allowed_durations_as_set = set(int(x) for x in allowed_durations_str.split(",") if x)
        if not jira_id or not re.match(r"^[A-Z][A-Z0-9]+-\d+$", jira_id):
            return {"statusCode": 200, "body": "Invalid Jira ID. Example: ENG-1234 Justification;30"}
        if not justification:
            return {"statusCode": 200, "body": "Justification required. Example: ENG-1234 Justification;30"}
        if minutes not in allowed_durations_as_set:
            return {
                "statusCode": 200,
                "body": "Duration must be one of: " + ", ".join(map(str, sorted(list(allowed_durations_as_set)))),
            }
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        now_epoch = int(time.time())
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_epoch))
        expiry_epoch = now_epoch + minutes * 60
        expiry_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expiry_epoch))
        # Local date for GSI partition
        local_date = datetime.now(tz=LOCAL_TZ).date().isoformat()
        # TTL based on retention policy (years), not access window
        retention_ttl_epoch = now_epoch + ACCESS_REQUEST_RETENTION_YEARS * 365 * 24 * 3600

        item = {
            "request_id": str(uuid.uuid4()),
            "timestamp": now_iso,
            "local_date": local_date,
            "user_email": user_name,  # Slack username; map to email later if needed
            "duration_minutes": minutes,
            "justification": justification,
            "jira_issue_id": jira_id,
            "request_timestamp": now_iso,
            "expiry_timestamp": expiry_iso,
        }
        # TTL (retention) if table has TTL configured
        item["ttl"] = retention_ttl_epoch

        table.put_item(Item=item)
        return {"statusCode": 200, "body": f"Request received: {minutes} min; expires {expiry_iso}. Jira={jira_id}."}

    except ValueError as ve:
        logger.info("validation_error message=%s", str(ve))
        return {"statusCode": 200, "body": str(ve)}
    except Exception as e:
        logger.error("unhandled_error error=%s", repr(e))
        return {"statusCode": 500, "body": "internal error"}
