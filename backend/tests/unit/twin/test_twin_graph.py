from datetime import datetime, timezone

from app.features.twin.graph.ids import (
    app_id,
    device_id,
    domain_id,
    edge_id,
    infra_id,
)
from app.features.twin.graph.model import TwinGraph
from app.features.twin.graph.schemas import (
    TraverseRequest,
    TwinEdge,
    TwinNode,
)


def _build_sample_graph() -> TwinGraph:
    graph = TwinGraph()
    now = datetime.now(timezone.utc)

    nodes = [
        TwinNode(
            id=device_id(1),
            entity_type="device",
            layer="observed",
            label="laptop-1",
            properties={"client_ip": "10.0.0.12"},
            last_seen_at=now,
        ),
        TwinNode(
            id=app_id("com.google.chrome"),
            entity_type="app",
            layer="observed",
            label="Chrome",
            properties={"slug": "com.google.chrome"},
            last_seen_at=now,
        ),
        TwinNode(
            id=domain_id("example.com"),
            entity_type="domain",
            layer="observed",
            label="example.com",
            properties={"blocked": False},
            last_seen_at=now,
        ),
        TwinNode(
            id=infra_id("ec2_gateway"),
            entity_type="infra_component",
            layer="desired",
            label="EC2 gateway",
            properties={"kind": "ec2_gateway"},
        ),
        TwinNode(
            id=infra_id("dns_resolver"),
            entity_type="infra_component",
            layer="desired",
            label="TrustEdge DNS",
            properties={"kind": "dns_resolver"},
        ),
    ]
    for node in nodes:
        graph.add_node(node)

    edges = [
        TwinEdge(
            id=edge_id("runs", device_id(1), app_id("com.google.chrome")),
            source_id=device_id(1),
            target_id=app_id("com.google.chrome"),
            relation="runs",
            layer="observed",
            weight=1,
        ),
        TwinEdge(
            id=edge_id("queries", app_id("com.google.chrome"), domain_id("example.com")),
            source_id=app_id("com.google.chrome"),
            target_id=domain_id("example.com"),
            relation="queries",
            layer="observed",
            weight=5,
        ),
        TwinEdge(
            id=edge_id("routed_via", device_id(1), infra_id("ec2_gateway")),
            source_id=device_id(1),
            target_id=infra_id("ec2_gateway"),
            relation="routed_via",
            layer="desired",
            weight=1,
        ),
        TwinEdge(
            id=edge_id("terminates_at", infra_id("ec2_gateway"), infra_id("dns_resolver")),
            source_id=infra_id("ec2_gateway"),
            target_id=infra_id("dns_resolver"),
            relation="terminates_at",
            layer="desired",
            weight=1,
        ),
    ]
    for edge in edges:
        graph.add_edge(edge)
    return graph


def test_from_snapshot_round_trip():
    graph = _build_sample_graph()
    snapshot = graph.to_snapshot(
        generated_at=datetime.now(timezone.utc),
        window_minutes=60,
    )
    restored = TwinGraph.from_snapshot(snapshot)
    assert len(restored.nodes) == len(graph.nodes)
    assert len(restored.edges) == len(graph.edges)


def test_traverse_forward_from_device():
    graph = _build_sample_graph()
    result = graph.traverse(
        TraverseRequest(
            seed_node_ids=[device_id(1)],
            direction="out",
            max_depth=3,
            layers=["observed", "desired"],
        )
    )
    node_ids = {node.id for node in result.nodes}
    assert app_id("com.google.chrome") in node_ids
    assert domain_id("example.com") in node_ids
    assert infra_id("ec2_gateway") in node_ids


def test_neighbors_bidirectional_filter():
    graph = _build_sample_graph()
    out_neighbors = graph.neighbors(device_id(1), direction="out", layers=["observed"])
    relations = {edge.relation for edge in out_neighbors}
    assert "runs" in relations
    assert "queries" not in relations

    both = graph.neighbors(infra_id("ec2_gateway"), direction="both", layers=["desired"])
    assert any(edge.relation == "terminates_at" for edge in both)
