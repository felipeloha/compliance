---
name: cdaa-integration-tests
description: Running or writing CDAA integration tests. Use when implementing, extending, or debugging tests in cdaa/tests/test_integration.py.
---

# CDAA Integration Tests

## Test setup

Integration tests use a real localstack instance as the AWS target.
**Terraform deploys the application Lambdas, DynamoDB table, and SSM parameters.**
Pytest fixtures handle the test-only infrastructure (stub Jira Lambda, SSM value overrides).

### Step 1 - Start localstack

```bash
cd cdaa
docker-compose up -d
```

Wait until localstack is healthy: `curl -s http://localhost:4566/_localstack/health | jq .services`

### Step 2 - Apply Terraform against localstack

Create `cdaa/terraform/provider_override.tf` (git-ignored, never commit):

```hcl
provider "aws" {
  region     = "us-east-1"
  access_key = "test"
  secret_key = "test"

  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    dynamodb   = "http://localhost:4566"
    lambda     = "http://localhost:4566"
    ssm        = "http://localhost:4566"
    iam        = "http://localhost:4566"
    logs       = "http://localhost:4566"
    sts        = "http://localhost:4566"
    cloudwatch = "http://localhost:4566"
  }
}
```

Create `cdaa/terraform/terraform.tfvars.localstack`:

```hcl
name_prefix                       = "cdaa-test"
account_id                        = "123456789012"
aws_region                        = "us-east-1"
jira_project_key                  = "PROJ"
jira_connector_function_name      = "cdaa-test-jira-stub"
rds_postgresql_loggroup_name      = "/aws/rds/instance/test-db/postgresql"
vault_audit_loggroup_name         = "/vault/audit"
database_audit_filter             = "example_prod_db"
cloudtrail_lake_curated_store_id  = "test-curated-store-id"
```

`cloudtrail_lake_curated_store_id` must be a non-empty string so the reconciliation
Lambda executes the curated-store query path (second StartQuery/GetQueryResults pair).

Apply only the resources localstack supports (CloudTrail Lake and API Gateway are not
needed for integration tests):

```bash
cd cdaa/terraform

terraform init

terraform apply -var-file=terraform.tfvars.localstack \
  -target=aws_dynamodb_table.access_requests \
  -target=aws_lambda_function.slack_access_request_handler \
  -target=aws_lambda_function.daily_reconciliation \
  -target=aws_lambda_function.audit_log_ctl_forwarder \
  -target=aws_ssm_parameter.slack_signing_secret \
  -target=aws_ssm_parameter.slack_bot_token \
  -target=aws_ssm_parameter.config_allowed_durations \
  -target=aws_ssm_parameter.config_customer_data \
  -target=aws_ssm_parameter.config_whitelist_db_users \
  -target=aws_ssm_parameter.config_whitelist_s3_actors \
  -target=aws_ssm_parameter.config_jira_reporting_enabled \
  -target=aws_iam_role.lambda_role
```

### Step 3 - Run the tests

```bash
cd cdaa/tests
uv sync
uv run pytest test_integration.py -v
```

---

## What Terraform creates vs what fixtures create

| Resource | Created by |
|---|---|
| DynamoDB `cdaa-test-requests` + all GSIs | Terraform |
| SSM params (with `CHANGE_ME` placeholders) | Terraform |
| Lambda `cdaa-test-slack-access-request-handler` | Terraform |
| Lambda `cdaa-test-daily-reconciliation` | Terraform |
| Lambda `cdaa-test-log-ctl-forwarder` | Terraform |
| SSM param values overwritten with test values | `ssm_params` fixture |
| Lambda `cdaa-test-jira-stub` | `stub_jira_lambda` fixture |
| DynamoDB `cdaa-test-jira-captures` capture table | `jira_capture_table` fixture |

The `ssm_params` fixture always runs with `Overwrite=True`, so it is safe to run
multiple times without re-applying Terraform.

---

## Constants in conftest.py

All resource names derive from `NAME_PREFIX = "cdaa-test"`. If you change the
`name_prefix` in `terraform.tfvars.localstack`, update this constant to match.

```python
NAME_PREFIX       = "cdaa-test"
TABLE_NAME        = f"{NAME_PREFIX}-requests"
SSM_PREFIX        = f"/audit/{NAME_PREFIX}"
SLACK_HANDLER_FN  = f"{NAME_PREFIX}-slack-access-request-handler"
CTL_FORWARDER_FN  = f"{NAME_PREFIX}-log-ctl-forwarder"
RECONCILIATION_FN = f"{NAME_PREFIX}-daily-reconciliation"
JIRA_STUB_FN      = f"{NAME_PREFIX}-jira-stub"
```

---

## CloudTrail Lake — pytest-httpserver

LocalStack community does not support CloudTrail Lake queries. The `ctl_httpserver`
session fixture (in `conftest.py`) starts a `pytest-httpserver` server on port `9090`
and sets `AWS_ENDPOINT_URL_CLOUDTRAIL=http://<host>:9090` on the reconciliation Lambda.
This is a boto3 service-specific endpoint override (requires boto3 >= 1.28).

- Calling `update_function_configuration` forces a cold start, so the module-level
  `boto3.client("cloudtrail")` in `daily_reconciliation.py` picks up the new endpoint.
- DynamoDB and Lambda invocations are unaffected; they continue routing through
  localstack via its own injected `AWS_ENDPOINT_URL`.

**Host networking**: the Lambda container (running inside Docker) must reach the test
machine's httpserver.

| Platform | Set `CTL_HTTPSERVER_HOST` to |
|---|---|
| Mac / Windows Docker Desktop | `host.docker.internal` (default) |
| Linux | `export CTL_HTTPSERVER_HOST=$(ip route show default \| awk '/default/{print $3}')` |

The reconciliation Lambda makes **two** StartQuery/GetQueryResults pairs per invocation
(S3 native store + curated store). Register **4 ordered handlers** per test case:

```python
ctl_httpserver.clear()
for query_id in ("q-s3", "q-curated"):
    ctl_httpserver.expect_ordered_request(
        "/", headers={"X-Amz-Target": CTL_TARGET_START_QUERY}
    ).respond_with_json({"QueryId": query_id})
    ctl_httpserver.expect_ordered_request(
        "/", headers={"X-Amz-Target": CTL_TARGET_GET_RESULTS}
    ).respond_with_json({
        "QueryStatus": "FINISHED",
        "QueryResultRows": rows,
        "QueryStatistics": {},
    })
```

The `QueryResultRows` format is a list of rows; each row is a list of
single-key dicts (one per column):

```python
[
    [
        {"eventTime":    "2024-01-15 10:30:00"},
        {"eventName":    "GetObject"},
        {"eventSource":  "s3.amazonaws.com"},
        {"principalId":  "ABCDE:alice@example.com"},
        {"reqBucketName":"example-data-bucket"},
        {"reqObjectKey": "customer/data.csv"},
    ]
]
```

---

## Test case strategy

**Cases 1-5** (Slack handler, CTL forwarder): invoke the Terraform-deployed Lambda via
`localstack_client("lambda").invoke(FunctionName=..., Payload=...)`. Assert on the
Lambda response and DynamoDB state.

**Cases 6-8** (reconciliation): use the `ctl_httpserver` fixture to pre-register
CloudTrail Lake responses, invoke the Terraform-deployed reconciliation Lambda via
`localstack_client("lambda").invoke(...)`, then assert against the `jira_capture_table`
to verify what the Lambda sent to the Jira connector.

Dependencies are managed via `pyproject.toml` in `cdaa/tests/`. Run `uv sync` to install.
