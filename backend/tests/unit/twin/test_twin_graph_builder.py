from datetime import datetime, timezone

import pytest

from app.features.network_attribution.models.device_network_context import DeviceNetworkContext
from app.features.twin.graph.builder import TwinGraphBuilder
from app.features.twin.graph.ids import app_id, device_id, infra_id
from app.features.twin.graph.model import TwinGraph
from app.shared.config import settings
from tests.helpers.factories import create_device


@pytest.fixture(autouse=True)
def enable_attribution(monkeypatch):
    monkeypatch.setattr(settings, "NETWORK_ATTRIBUTION_ENABLED", True)


def test_builder_includes_observed_layers(db_session):
    device = create_device(db_session, external_id="graph-builder")
    now = datetime.now(timezone.utc)
    db_session.add(
        DeviceNetworkContext(
            device_id=device.id,
            app_slug="zoom",
            app_display_name="Zoom",
            bundle_id="us.zoom.xos",
            observed_at=now,
        )
    )
    db_session.commit()

    snapshot = TwinGraphBuilder(db_session).build(minutes=15, include_flows=False)
    graph = TwinGraph.from_snapshot(snapshot)

    assert device_id(device.id) in graph.nodes
    assert app_id("zoom") in graph.nodes
    assert infra_id("ec2_gateway") in graph.nodes

    layers = {node.layer for node in graph.nodes.values()}
    assert "observed" in layers
    assert "desired" in layers
