import base64
import gzip
import hashlib
import hmac
import json
import time
import uuid
from decimal import Decimal
from urllib.parse import urlencode

import pytest

from conftest import (
    CTL_FORWARDER_FN,
    RECONCILIATION_FN,
    SLACK_HANDLER_FN,
)

# ---------------------------------------------------------------------------
# Phase 0 - infrastructure smoke test
# ---------------------------------------------------------------------------

SMOKE_ITEM = {
    "request_id": "smoke-test-id",
    "timestamp": "1970-01-01T00:00:00Z",
}


def test_phase0_infrastructure_ready(dynamodb_table, ssm_params):
    """
    Confirm Terraform has been applied and localstack is healthy.
    Writes a known item, reads it back, then deletes it.
    Implicitly validates SSM params are writable (ssm_params fixture).
    """
    dynamodb_table.put_item(Item=SMOKE_ITEM)
    result = dynamodb_table.get_item(Key=SMOKE_ITEM)
    print(f"\n  [phase0] DynamoDB round-trip item: {result['Item']}")
    print(f"  [phase0] SSM params written: {list(ssm_params.keys())}")
    assert "Item" in result
    dynamodb_table.delete_item(Key=SMOKE_ITEM)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SLACK_SIGNING_SECRET = "test-signing-secret"  # matches ssm_params fixture


def _make_slack_event(form: dict, secret: str = _SLACK_SIGNING_SECRET) -> dict:
    """Build a signed API Gateway HTTP v2 event for the Slack handler Lambda."""
    body = urlencode(form)
    ts = str(int(time.time()))
    basestring = f"v0:{ts}:{body}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), basestring, hashlib.sha256).hexdigest()
    return {
        "body": body,
        "isBase64Encoded": False,
        "headers": {
            "x-slack-request-timestamp": ts,
            "x-slack-signature": f"v0={digest}",
        },
    }


def _invoke(localstack_client, fn_name: str, payload: dict) -> dict:
    """Invoke a Lambda synchronously and return the parsed response dict."""
    lam = localstack_client("lambda")
    resp = lam.invoke(FunctionName=fn_name, InvocationType="RequestResponse", Payload=json.dumps(payload))
    return json.loads(resp["Payload"].read())


def _make_cwl_event(messages: list[str], log_group: str = "/aws/rds/instance/test-db/postgresql") -> dict:
    """Build a CloudWatch Logs subscription event (gzip+base64 encoded)."""
    inner = {
        "messageType": "DATA_MESSAGE",
        "owner": "123456789012",
        "logGroup": log_group,
        "logStream": "test-stream",
        "subscriptionFilters": ["test-filter"],
        "logEvents": [{"id": f"e{i}", "timestamp": 1_700_000_000_000, "message": m} for i, m in enumerate(messages)],
    }
    data = base64.b64encode(gzip.compress(json.dumps(inner).encode())).decode()
    return {"awslogs": {"data": data}}


# ---------------------------------------------------------------------------
# Slack handler - Cases 1-4
# ---------------------------------------------------------------------------


def test_slack_invalid_signature(localstack_client, ssm_params):
    """Lambda rejects requests signed with a wrong secret."""
    event = _make_slack_event({"text": "PROJ-1 test;30"}, secret="wrong-secret")
    result = _invoke(localstack_client, SLACK_HANDLER_FN, event)
    print(f"\n  [slack/invalid_sig] Lambda response: {result}")
    assert result["statusCode"] == 200
    assert "invalid signature" in result["body"]


def test_slack_plaintext_valid_request(localstack_client, dynamodb_table, ssm_params):
    """Valid plaintext slash command writes an access request to DynamoDB."""
    form = {
        "user_id": "U12345",
        "user_name": "alice",
        "text": "PROJ-999 need prod access for incident;30",
    }
    result = _invoke(localstack_client, SLACK_HANDLER_FN, _make_slack_event(form))
    print(f"\n  [slack/valid] Lambda response: {result}")

    items = dynamodb_table.scan(
        FilterExpression="jira_issue_id = :j",
        ExpressionAttributeValues={":j": "PROJ-999"},
    ).get("Items", [])
    print(f"  [slack/valid] DynamoDB item written: {items[0] if items else 'NONE'}")
    assert result["statusCode"] == 200
    assert "Request received" in result["body"]
    assert len(items) == 1
    assert items[0]["duration_minutes"] == 30
    assert items[0]["justification"] == "need prod access for incident"


def test_slack_plaintext_invalid_jira_id(localstack_client, ssm_params):
    """Malformed Jira ID returns guidance text, nothing written to DynamoDB."""
    form = {"user_id": "U1", "user_name": "bob", "text": "not-a-jira-id some reason;30"}
    result = _invoke(localstack_client, SLACK_HANDLER_FN, _make_slack_event(form))
    print(f"\n  [slack/bad_jira] Lambda response: {result}")
    assert result["statusCode"] == 200
    assert "Invalid Jira ID" in result["body"]


def test_slack_plaintext_invalid_duration(localstack_client, ssm_params):
    """Duration not in the configured allowed list returns guidance text."""
    form = {"user_id": "U1", "user_name": "bob", "text": "PROJ-1 some reason;999"}
    result = _invoke(localstack_client, SLACK_HANDLER_FN, _make_slack_event(form))
    print(f"\n  [slack/bad_duration] Lambda response: {result}")
    assert result["statusCode"] == 200
    assert "Duration must be one of" in result["body"]


# ---------------------------------------------------------------------------
# CTL forwarder - Cases 5-7
# ---------------------------------------------------------------------------


def test_ctl_forwarder_unparseable_logs(localstack_client):
    """Messages matching no pattern are skipped; CloudTrail is never called."""
    event = _make_cwl_event(["this is not a parseable log line", "another random line"])
    result = _invoke(localstack_client, CTL_FORWARDER_FN, event)
    body = json.loads(result["body"])
    print(f"\n  [ctl/unparseable] Lambda response: status={result['statusCode']} body={body}")
    assert result["statusCode"] == 200
    assert body["emitted"] == 0


def test_ctl_forwarder_db_filtered_out(localstack_client):
    """Valid PG connect log for a DB not in DATABASE_FILTER is dropped."""
    pg_msg = (
        "2024-01-15 10:30:00 UTC:10.0.0.1(1234):alice@other_db:[9999]:LOG: "
        " connection authorized: user=alice database=other_db"
    )
    result = _invoke(localstack_client, CTL_FORWARDER_FN, _make_cwl_event([pg_msg]))
    body = json.loads(result["body"])
    print(f"\n  [ctl/db_filtered] Lambda response: status={result['statusCode']} body={body}")
    assert result["statusCode"] == 200
    assert body["emitted"] == 0


def test_ctl_forwarder_vault_non_prod_path(localstack_client):
    """Vault log for a non-prod creds path (no 'prod-' prefix) is not forwarded."""
    vault_msg = json.dumps({
        "time": "2024-01-15T10:30:00Z",
        "request": {"path": "database/creds/dev-ro"},
        "response": {},
    })
    result = _invoke(localstack_client, CTL_FORWARDER_FN, _make_cwl_event([vault_msg], log_group="/vault/audit"))
    body = json.loads(result["body"])
    print(f"\n  [ctl/vault_non_prod] Lambda response: status={result['statusCode']} body={body}")
    assert result["statusCode"] == 200
    assert body["emitted"] == 0


# ---------------------------------------------------------------------------
# Reconciliation Lambda - Cases R1-R4
# ---------------------------------------------------------------------------


def _register_ctl_handlers(ctl_httpserver, s3_rows: list, curated_rows: list) -> None:
    """Register ordered CloudTrail Lake mock handlers for one reconciliation run.

    The reconciliation Lambda fires exactly four requests in order:
      1. StartQuery  (S3 store)
      2. GetQueryResults (S3 store)
      3. StartQuery  (curated store)
      4. GetQueryResults (curated store)

    We register plain ordered handlers without header constraints because
    werkzeug may normalize header case differently than boto3 sends them,
    making exact header matching unreliable in this Lambda+Docker setup.
    """
    # QueryId must be ≥36 chars (UUID) to pass boto3 CloudTrail client validation.
    _UUID_S3 = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
    _UUID_CTL = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"

    ctl_httpserver.clear()
    for query_id, rows in ((_UUID_S3, s3_rows), (_UUID_CTL, curated_rows)):
        ctl_httpserver.expect_ordered_request("/").respond_with_json({"QueryId": query_id})
        ctl_httpserver.expect_ordered_request("/").respond_with_json(
            {"QueryStatus": "FINISHED", "QueryResultRows": rows, "QueryStatistics": {}}
        )


def _invoke_reconciliation(localstack_client, window_start: str, window_end: str) -> dict:
    """Invoke the reconciliation Lambda with an explicit UTC time window."""
    lam = localstack_client("lambda")
    resp = lam.invoke(
        FunctionName=RECONCILIATION_FN,
        InvocationType="RequestResponse",
        Payload=json.dumps({"start": window_start, "end": window_end}),
    )
    if "FunctionError" in resp:
        payload = json.loads(resp["Payload"].read())
        pytest.fail(f"Reconciliation Lambda raised: {payload}")
    return json.loads(resp["Payload"].read())


def _s3_row(event_time: str, request_id: str = "req-test") -> list:
    """Build a CloudTrail Lake S3 query result row for alice@example.com.

    Column order matches the SELECT list in DailyReconciliationService._build_s3_query.
    """
    return [
        {"eventTime": event_time},
        {"eventName": "GetObject"},
        {"eventSource": "s3.amazonaws.com"},
        {"awsRegion": "eu-central-1"},
        {"sourceIpAddress": "203.0.113.5"},
        {"userAgent": "aws-sdk-python"},
        {"userIdentityType": "AssumedRole"},
        {"principalId": "AROAEXAMPLE:alice@example.com"},
        {"userIdentityArn": "arn:aws:sts::123456789012:assumed-role/SSORole/alice@example.com"},
        {"sessionIssuerUserName": "AWSReservedSSO_AdministratorAccess"},
        {"recipientAccountId": "123456789012"},
        {"requestID": request_id},
        {"reqBucketName": "example-data-bucket"},
        {"reqObjectKey": "customer/data.csv"},
    ]


_DB_CONNECT_ROW = [
    {"eventTime": "2024-01-13 10:30:00"},
    {"eventName": "DbSessionConnect"},
    {"auth_display_name": None},
    {"db_username": "app_user"},
    {"database": "example_prod_db"},
    {"path": None},
    {"lease_id": None},
    {"sourceIpAddress": "10.0.0.1"},
    {"userAgent": "psql"},
]


def test_reconciliation_no_violations(localstack_client, ctl_httpserver, ssm_params):
    """Both stores return no events: report has 0 violations and no Jira calls."""
    _register_ctl_handlers(ctl_httpserver, s3_rows=[], curated_rows=[])
    report = _invoke_reconciliation(localstack_client, "2024-01-10T00:00:00Z", "2024-01-10T23:59:59Z")
    summary = report["execution_summary"]
    print(f"\n  [recon/no_violations] summary: {summary}")
    assert summary["total_violations_found"] == 0


def test_reconciliation_s3_unauthorized_access(
    localstack_client, ctl_httpserver, ssm_params, stub_jira_lambda, jira_httpserver
):
    """S3 GetObject by alice with no approved request → 1 human violation → Jira ticket."""
    jira_httpserver.clear()
    jira_httpserver.expect_ordered_request("/").respond_with_json({"ok": True})
    _register_ctl_handlers(ctl_httpserver, s3_rows=[_s3_row("2024-01-11 10:30:00", "req-r2")], curated_rows=[])
    report = _invoke_reconciliation(localstack_client, "2024-01-11T00:00:00Z", "2024-01-11T23:59:59Z")
    summary = report["execution_summary"]
    actor_counts = report["violations_by_actor_type"]
    human_violations = report["violations_grouped"]["human_violations"]
    print(f"\n  [recon/s3_unauth] summary: {summary}")
    print(f"  [recon/s3_unauth] actor_counts: {actor_counts}")
    assert summary["total_violations_found"] == 1
    assert actor_counts["human_actors"] == 1
    assert len(human_violations) == 1
    assert human_violations[0]["user_email"] == "alice@example.com"

    jira_httpserver.check_assertions()
    request, _ = jira_httpserver.log[-1]
    ticket = json.loads(request.get_data())
    print(f"  [recon/s3_unauth] Jira ticket: project={ticket['project_key']} summary={ticket['summary']!r}")
    assert ticket["project_key"] == "PROJ"
    assert "alice@example.com" in ticket["summary"]


def test_reconciliation_access_within_approved_window(
    localstack_client, ctl_httpserver, ssm_params, stub_jira_lambda, dynamodb_table
):
    """S3 GetObject within alice's 60-min approved window → 0 violations → no Jira ticket."""
    # Insert an approved request: window 2024-01-12 10:00–11:00 UTC
    req_item = {
        "request_id": "test-recon-r3",
        "timestamp": "2024-01-12T10:00:00Z",
        "local_date": "2024-01-12",
        "user_email": "alice@example.com",
        "user_id": "U12345",
        "user_name": "alice",
        "duration_minutes": Decimal("60"),
        "jira_issue_id": "PROJ-100",
        "justification": "approved incident response",
    }
    dynamodb_table.put_item(Item=req_item)

    # Event at 10:30 — inside the approved window
    _register_ctl_handlers(ctl_httpserver, s3_rows=[_s3_row("2024-01-12 10:30:00", "req-r3")], curated_rows=[])
    report = _invoke_reconciliation(localstack_client, "2024-01-12T00:00:00Z", "2024-01-12T23:59:59Z")
    summary = report["execution_summary"]
    print(f"\n  [recon/approved_window] summary: {summary}")
    assert summary["total_violations_found"] == 0
    assert report["violations_grouped"]["human_violations"] == []


def test_reconciliation_db_unauthorized_access(
    localstack_client, ctl_httpserver, ssm_params, stub_jira_lambda, jira_httpserver
):
    """DB connect event with no approved request → 1 non-human violation → Jira ticket."""
    jira_httpserver.clear()
    jira_httpserver.expect_ordered_request("/").respond_with_json({"ok": True})
    _register_ctl_handlers(ctl_httpserver, s3_rows=[], curated_rows=[_DB_CONNECT_ROW])
    report = _invoke_reconciliation(localstack_client, "2024-01-13T00:00:00Z", "2024-01-13T23:59:59Z")
    summary = report["execution_summary"]
    actor_counts = report["violations_by_actor_type"]
    non_human = report["violations_grouped"]["non_human_violations"]
    print(f"\n  [recon/db_unauth] summary: {summary}")
    print(f"  [recon/db_unauth] actor_counts: {actor_counts}")
    print(f"  [recon/db_unauth] non_human: {non_human}")
    assert summary["total_violations_found"] == 1
    assert actor_counts["human_actors"] == 0
    assert non_human["total_count"] == 1

    jira_httpserver.check_assertions()
    request, _ = jira_httpserver.log[-1]
    ticket = json.loads(request.get_data())
    print(f"  [recon/db_unauth] Jira ticket: project={ticket['project_key']} summary={ticket['summary']!r}")
    assert ticket["project_key"] == "PROJ"
    assert "service or unknown actor" in ticket["summary"]
