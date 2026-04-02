import base64
import gzip
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from conftest import CTL_FORWARDER_FN, SLACK_HANDLER_FN

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
