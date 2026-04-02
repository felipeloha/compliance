# Phase 0 marker - infrastructure smoke test
# Real integration test cases (Cases 1-8) are added in subsequent tasks.

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
    assert "Item" in result
    dynamodb_table.delete_item(Key=SMOKE_ITEM)
