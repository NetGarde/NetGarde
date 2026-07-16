from app.features.twin.graph.builder import TwinGraphBuilder
from app.features.twin.graph.ids import infra_id
from app.features.twin.graph.model import TwinGraph


def test_builder_includes_infra_layers(db_session):
    snapshot = TwinGraphBuilder(db_session).build(minutes=15, include_flows=False)
    graph = TwinGraph.from_snapshot(snapshot)

    assert infra_id("ec2_gateway") in graph.nodes
    layers = {node.layer for node in graph.nodes.values()}
    assert "desired" in layers
