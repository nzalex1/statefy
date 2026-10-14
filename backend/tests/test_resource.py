
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.resource import Resource, ResourceStatus


def test_create_resource():
    resource = Resource(
        id="prod-network",
        name="Production Network",
        provider="terraform",
        environment="production",
    )

    assert resource.id == "prod-network"
    assert resource.status == ResourceStatus.UNKNOWN
    assert resource.desired_state == {}
    assert resource.observed_state == {}
    assert resource.last_reconciled is None


def test_resource_with_desired_state():
    resource = Resource(
        id="prod-network",
        name="Production Network",
        provider="terraform",
        environment="production",
        desired_state={
            "region": "australiaeast",
            "resource_group": "rg-production",
        },
    )

    assert resource.desired_state["region"] == "australiaeast"


def test_invalid_resource():
    with pytest.raises(ValidationError):
        Resource(
            id="prod-network",
            name="Production Network",
            provider="terraform",
            environment=None,
        )


def test_resource_timestamp():
    before = datetime.now(timezone.utc)

    resource = Resource(
        id="test",
        name="Test",
        provider="powershell",
        environment="dev",
    )

    after = datetime.now(timezone.utc)

    assert before <= resource.created_at <= after
