from datetime import datetime, timezone
from unittest.mock import patch

from app.features.twin.graph.builder import TwinGraphBuilder
from app.features.twin.graph.ids import app_id, infra_id
from app.features.twin.graph.model import TwinGraph
from app.features.twin.services.trusttwin_store import TwinDeviceLatest, twin_device_node_id
from app.shared.config import settings


def test_builder_ingests_trusttwin_security_destinations(db_session, monkeypatch):
    """Security map: client identity + egress path + port destinations (not host posture)."""
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
        network_summary={
            "public_ip": "203.0.113.10",
            "network_type": "wifi",
            "established_count": 5,
            "top_remote_ports": [
                {
                    "port": 443,
                    "count": 28,
                    "app_name": "Code",
                    "bundle_id": "com.microsoft.VSCode",
                },
                {
                    "port": 5223,
                    "count": 4,
                    "app_name": "Slack",
                    "bundle_id": "com.tinyspeck.slackmacgap",
                },
            ],
        },
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
    assert node.properties["public_ip"] == "203.0.113.10"
    assert node.properties["client_ip"] == "203.0.113.10"
    # Host posture stays on properties only.
    assert node.properties["presence"] == "active"
    assert node.properties["os"] == "darwin"

    # No host-posture nodes; processes are attributed on destinations.
    assert f"infra:tt:dev_mbp:tt_os" not in graph.nodes
    assert f"infra:tt:dev_mbp:tt_agent" not in graph.nodes
    assert f"infra:tt:dev_mbp:tt_presence" not in graph.nodes
    assert f"infra:tt:dev_mbp:tt_established" not in graph.nodes
    assert app_id("com-microsoft-vscode") in graph.nodes
    assert app_id("com-tinyspeck-slackmacgap") in graph.nodes
    assert app_id("cat-development") not in graph.nodes

    # Client → LAN → Internet → public IP.
    public_net = infra_id("public_network")
    lan_nid = f"infra:tt:dev_mbp:tt_lan"
    assert public_net in graph.nodes
    assert lan_nid in graph.nodes
    routed_obs = graph.neighbors(
        device_nid,
        direction="out",
        relations=["routed_via"],
        layers=["observed"],
    )
    assert {edge.target_id for edge in routed_obs} == {lan_nid}
    lan_out = graph.neighbors(
        lan_nid,
        direction="out",
        relations=["routed_via"],
        layers=["observed"],
    )
    assert any(edge.target_id == public_net for edge in lan_out)

    # TrustTwin devices are not attached to the VPN infra chain.
    routed_vpn = graph.neighbors(
        device_nid,
        direction="out",
        relations=["routed_via"],
        layers=["desired"],
    )
    assert routed_vpn == []
    assert infra_id("ec2_gateway") in graph.nodes

    # Remote ports hang off Internet egress (not the client node).
    opens = graph.neighbors(
        public_net,
        direction="out",
        relations=["opens_direct"],
        layers=["observed"],
    )
    assert len(opens) == 2
    client_opens = graph.neighbors(
        device_nid,
        direction="out",
        relations=["opens_direct"],
        layers=["observed"],
    )
    assert client_opens == []
    assert snapshot.meta["trusttwin_devices"] == 1
