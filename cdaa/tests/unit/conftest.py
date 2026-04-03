"""
Unit-test conftest.

Overrides the session-scoped autouse fixture from the parent conftest so that
unit tests can run without localstack or any real AWS connectivity.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def truncate_requests_table():
    """No-op: unit tests do not touch DynamoDB."""
    pass
