"""
Integration test fixtures for CDAA.

Prerequisites: localstack running + Terraform applied against it.
See ai-docs/skills/cdaa-integration-tests/SKILL.md for setup steps.
"""

import io
import json
import os
import zipfile

import pytest

LOCALSTACK_ENDPOINT = "http://localhost:4566"
AWS_REGION = "us-east-1"
DUMMY_CREDS = {
    "aws_access_key_id": "test",
    "aws_secret_access_key": "test",
    "region_name": AWS_REGION,
    "endpoint_url": LOCALSTACK_ENDPOINT,
}

# Must match the name_prefix used in terraform.tfvars.localstack
NAME_PREFIX = "cdaa-test"

TABLE_NAME = f"{NAME_PREFIX}-requests"
SSM_PREFIX = f"/audit/{NAME_PREFIX}"
JIRA_STUB_TABLE = f"{NAME_PREFIX}-jira-captures"

# Lambda function names as Terraform creates them
SLACK_HANDLER_FN = f"{NAME_PREFIX}-slack-access-request-handler"
CTL_FORWARDER_FN = f"{NAME_PREFIX}-log-ctl-forwarder"
RECONCILIATION_FN = f"{NAME_PREFIX}-daily-reconciliation"
JIRA_STUB_FN = f"{NAME_PREFIX}-jira-stub"

# CloudTrail Lake mock server
# On Mac/Windows Docker Desktop use host.docker.internal.
# On Linux: export CTL_HTTPSERVER_HOST=$(ip route show default | awk '/default/{print $3}')
CTL_HTTPSERVER_PORT = 9090
CTL_HTTPSERVER_HOST = os.environ.get("CTL_HTTPSERVER_HOST", "host.docker.internal")

# X-Amz-Target values sent by the boto3 cloudtrail client
CTL_TARGET_START_QUERY = "CloudTrail_20131101.StartQuery"
CTL_TARGET_GET_RESULTS = "CloudTrail_20131101.GetQueryResults"


# ---------------------------------------------------------------------------
# Low-level client factory
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def localstack_client():
    """Return a factory that produces boto3 clients pointed at localstack."""
    import boto3

    def _factory(service: str):
        return boto3.client(service, **DUMMY_CREDS)

    return _factory


# ---------------------------------------------------------------------------
# DynamoDB: reference the table Terraform created
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def dynamodb_table(localstack_client):
    """
    Return the access_requests DynamoDB table created by Terraform.
    Fails fast if Terraform has not been applied.
    """
    import boto3

    resource = boto3.resource("dynamodb", **DUMMY_CREDS)
    table = resource.Table(TABLE_NAME)
    table.load()  # raises ResourceNotFoundException if Terraform wasn't applied
    return table


# ---------------------------------------------------------------------------
# SSM: overwrite Terraform placeholders with real test values
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ssm_params(localstack_client):
    """
    Write test values into the SSM parameters Terraform created.
    Terraform sets placeholder values (CHANGE_ME) for secrets; this fixture
    replaces them with usable test values before the Lambdas are invoked.
    """
    ssm = localstack_client("ssm")

    params = {
        f"{SSM_PREFIX}/slack_signing_secret": ("SecureString", "test-signing-secret"),
        f"{SSM_PREFIX}/slack_bot_token": ("SecureString", "xoxb-test-bot-token"),
        f"{SSM_PREFIX}/allowed_durations": ("String", "15,30,60,120"),
        f"{SSM_PREFIX}/customer_data_config": (
            "String",
            json.dumps(
                {
                    "s3_buckets": ["arn:aws:s3:::example-data-bucket"],
                    "rds_databases": ["arn:aws:rds:us-east-1:123456789012:db:example-prod"],
                }
            ),
        ),
        f"{SSM_PREFIX}/whitelist_db_users": ("String", json.dumps([])),
        f"{SSM_PREFIX}/whitelist_s3_actors": ("String", json.dumps({})),
        f"{SSM_PREFIX}/jira_reporting_enabled": ("String", "true"),
    }

    for name, (param_type, value) in params.items():
        ssm.put_parameter(Name=name, Value=value, Type=param_type, Overwrite=True)

    return {name: value for name, (_, value) in params.items()}


# ---------------------------------------------------------------------------
# Stub Jira Lambda (captures payload to DynamoDB for assertion)
# Terraform does not create this - it is test-only infrastructure.
# ---------------------------------------------------------------------------

_JIRA_STUB_CODE = '''
import json
import os
import boto3

def handler(event, context):
    # No explicit endpoint_url — localstack injects AWS_ENDPOINT_URL into the
    # Lambda container environment so boto3 routes calls to localstack automatically.
    ddb = boto3.resource("dynamodb")
    table = ddb.Table(os.environ["CAPTURE_TABLE"])
    table.put_item(Item={"id": context.aws_request_id, "payload": json.dumps(event)})
    return {"statusCode": 200, "body": "ok"}
'''


@pytest.fixture(scope="session")
def jira_capture_table(localstack_client):
    """DynamoDB table used by the stub Jira Lambda to record invocations."""
    import boto3

    client = localstack_client("dynamodb")
    resource = boto3.resource("dynamodb", **DUMMY_CREDS)

    try:
        table = resource.Table(JIRA_STUB_TABLE)
        table.load()
        return table
    except client.exceptions.ResourceNotFoundException:
        pass

    table = resource.create_table(
        TableName=JIRA_STUB_TABLE,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
    )
    table.wait_until_exists()
    return table


@pytest.fixture(scope="session")
def stub_jira_lambda(localstack_client, jira_capture_table):
    """
    Deploy the stub Jira Lambda into localstack.

    This is test-only infrastructure - not created by Terraform.
    The reconciliation Lambda points at JIRA_STUB_FN via its env var
    (set in terraform.tfvars.localstack as jira_connector_function_name).

    Tests read from jira_capture_table to assert what the reconciliation
    Lambda sent to the Jira connector.
    """
    lambda_client = localstack_client("lambda")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("handler.py", _JIRA_STUB_CODE)
    zip_bytes = buf.getvalue()

    env_vars = {
        "CAPTURE_TABLE": JIRA_STUB_TABLE,
    }

    try:
        lambda_client.get_function(FunctionName=JIRA_STUB_FN)
        lambda_client.update_function_code(FunctionName=JIRA_STUB_FN, ZipFile=zip_bytes)
        lambda_client.update_function_configuration(
            FunctionName=JIRA_STUB_FN,
            Environment={"Variables": env_vars},
        )
    except lambda_client.exceptions.ResourceNotFoundException:
        lambda_client.create_function(
            FunctionName=JIRA_STUB_FN,
            Runtime="python3.12",
            Role="arn:aws:iam::123456789012:role/test-role",
            Handler="handler.handler",
            Code={"ZipFile": zip_bytes},
            Environment={"Variables": env_vars},
            Timeout=10,
        )

    return JIRA_STUB_FN


# ---------------------------------------------------------------------------
# CloudTrail Lake mock (pytest-httpserver)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ctl_httpserver(localstack_client):
    """
    HTTP server that stands in for the CloudTrail Lake query API.

    LocalStack community edition does not support CloudTrail Lake, so this
    server intercepts the boto3 cloudtrail client by setting
    AWS_ENDPOINT_URL_CLOUDTRAIL on the reconciliation Lambda (boto3 >= 1.28
    service-specific endpoint override). All other service calls (DynamoDB,
    Lambda) continue through localstack via its own injected AWS_ENDPOINT_URL.

    Calling update_function_configuration forces a cold start on the next
    invocation, ensuring the module-level boto3.client("cloudtrail") in
    daily_reconciliation.py is recreated with the new endpoint.

    Per-test usage:
        def test_foo(ctl_httpserver, ...):
            ctl_httpserver.clear()
            ctl_httpserver.expect_ordered_request("/", headers={"X-Amz-Target": CTL_TARGET_START_QUERY}).respond_with_json({"QueryId": "q1"})
            ctl_httpserver.expect_ordered_request("/", headers={"X-Amz-Target": CTL_TARGET_GET_RESULTS}).respond_with_json({"QueryStatus": "FINISHED", "QueryResultRows": [...], "QueryStatistics": {}})
            # repeat for the curated-store query pair
    """
    from pytest_httpserver import HTTPServer

    server = HTTPServer(host="0.0.0.0", port=CTL_HTTPSERVER_PORT)
    server.start()

    lambda_client = localstack_client("lambda")
    cfg = lambda_client.get_function_configuration(FunctionName=RECONCILIATION_FN)
    current_env = cfg.get("Environment", {}).get("Variables", {})
    lambda_client.update_function_configuration(
        FunctionName=RECONCILIATION_FN,
        Environment={
            "Variables": {
                **current_env,
                "AWS_ENDPOINT_URL_CLOUDTRAIL": f"http://{CTL_HTTPSERVER_HOST}:{CTL_HTTPSERVER_PORT}",
            }
        },
    )

    yield server

    server.clear()
    server.stop()


# ---------------------------------------------------------------------------
# Session-scoped cleanup: truncate tables before the test session runs
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def truncate_requests_table(dynamodb_table):
    """Delete all items from the access_requests table before the session."""
    _truncate_table(dynamodb_table, ["request_id", "timestamp"])


@pytest.fixture(scope="session", autouse=True)
def truncate_jira_captures(jira_capture_table):
    """Delete all items from the jira-captures table before the session."""
    _truncate_table(jira_capture_table, ["id"])


def _truncate_table(table, key_names: list[str]) -> None:
    expr_names = {f"#{k}": k for k in key_names}
    projection = ", ".join(expr_names.keys())

    response = table.scan(ProjectionExpression=projection, ExpressionAttributeNames=expr_names)
    with table.batch_writer() as batch:
        for item in response.get("Items", []):
            batch.delete_item(Key={k: item[k] for k in key_names})
    while "LastEvaluatedKey" in response:
        response = table.scan(
            ProjectionExpression=projection,
            ExpressionAttributeNames=expr_names,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        with table.batch_writer() as batch:
            for item in response.get("Items", []):
                batch.delete_item(Key={k: item[k] for k in key_names})
