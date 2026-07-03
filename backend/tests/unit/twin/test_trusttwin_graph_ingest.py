from datetime import datetime, timezone
from unittest.mock import patch

from app.features.twin.graph.builder import TwinGraphBuilder
from app.features.twin.graph.ids import app_id, infra_id
from app.features.twin.graph.model import TwinGraph
from app.features.twin.services.trusttwin_store import TwinDeviceLatest, twin_device_node_id
from app.shared.config import settings


def test_builder_ingests_trusttwin_device_and_apps(db_session, monkeypatch):
    monkeypatch.setattr(settings, "NETWORK_ATTRIBUTION_ENABLED", True)
    monkeypatch.setattr(settings, "NETWORK_FLOWS_ENABLED", False)

    rec = TwinDeviceLatest(
        device_id="dev_mbp",
        last_seen_at=datetime(2026, 7, 4, tzinfo=timezone.utc),
        client_details={
            "hostname": "elad-mbp",
            "os": "darwin",
            "status": "online",
        },
        network_summary={"public_ip": "8.8.8.8", "established_count": 5},
        action_summary={
            "presence": "active",
            "focus": [
                {
                    "app_name": "Code",
                    "bundle_id": "com.microsoft.VSCode",
                    "category": "development",
                    "duration_sec": 55,
                }
            ],
        },
    )

    with patch(
        "app.features.twin.graph.builder.trusttwin_store.list_latest",
        return_value=[rec],
    ):
        snapshot = TwinGraphBuilder(db_session).build(
            minutes=1,
            include_flows=False,
            include_policy=False,
            include_trusttwin=True,
        )

    graph = TwinGraph.from_snapshot(snapshot)
    device_nid = twin_device_node_id("dev_mbp")
    assert device_nid in graph.nodes
    node = graph.nodes[device_nid]
    assert node.label == "elad-mbp"
    assert node.properties["source"] == "trusttwin"
    assert node.properties["public_ip"] == "8.8.8.8"
    assert node.properties["presence"] == "active"

    code_nid = app_id("com-microsoft-vscode")
    assert code_nid in graph.nodes
    runs = graph.neighbors(device_nid, direction="out", relations=["runs"], layers=["observed"])
    assert any(edge.target_id == code_nid for edge in runs)

    # TrustTwin devices are not attached to the VPN infra chain.
    routed = graph.neighbors(
        device_nid,
        direction="out",
        relations=["routed_via"],
        layers=["desired"],
    )
    assert routed == []
    assert infra_id("wireguard") in graph.nodes
    assert snapshot.meta["trusttwin_devices"] == 1
