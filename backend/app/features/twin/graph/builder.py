from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Set

from sqlalchemy.orm import Session

from app.features.network_attribution.schemas.network_attribution import (
    NetworkMapEdge,
    NetworkMapNode,
    NetworkMapResponse,
)
from app.features.network_attribution.services.network_attribution_service import (
    NetworkAttributionService,
)
from app.features.network_flows.services.flow_map_service import merge_flows_into_map
from app.features.network_flows.services.flow_store import StoredFlow, list_recent_flows
from app.features.twin.graph.ids import (
    app_id,
    domain_id,
    edge_id,
    flow_session_id,
    infra_id,
    ip_id,
    l4_service_id,
)
from app.features.twin.graph.model import TwinGraph
from app.features.twin.graph.schemas import TwinEdge, TwinGraphSnapshot, TwinLayer, TwinNode
from app.features.twin.services import trusttwin_store
from app.shared.config import settings
from app.shared.domain_utils import extract_root_domain


MAP_EDGE_TO_RELATION: dict[str, str] = {
    "foreground": "runs",
    "dns": "queries",
    "dns_direct": "queries_direct",
    "dns_to_flow": "correlates",
}

INFRA_CHAIN: tuple[tuple[str, str, str], ...] = (
    ("ec2_gateway", "dns_resolver", "terminates_at"),
)


@dataclass
class _BuilderState:
    nodes: Dict[str, TwinNode] = field(default_factory=dict)
    edges: Dict[str, TwinEdge] = field(default_factory=dict)
    observed_domains: Set[str] = field(default_factory=set)
    device_profiles: Dict[int, int] = field(default_factory=dict)


class TwinGraphBuilder:
    """Assemble canonical twin graph from attribution, flows, and policy state."""

    def __init__(self, db: Session):
        self.db = db
        self.state = _BuilderState()

    def build(
        self,
        *,
        minutes: int = 1,
        include_flows: bool = True,
        include_policy: bool = True,
        include_trusttwin: bool = True,
    ) -> TwinGraphSnapshot:
        attribution = NetworkAttributionService(self.db)
        base_map = attribution.build_map(minutes=minutes)
        if include_flows and settings.NETWORK_FLOWS_ENABLED:
            base_map = merge_flows_into_map(base_map, minutes=minutes)

        self._ingest_observed_map(base_map)
        if include_flows and settings.NETWORK_FLOWS_ENABLED:
            self._ingest_flow_resolutions(minutes=minutes)
        trusttwin_count = 0
        if include_trusttwin:
            trusttwin_count = self._ingest_trusttwin()
        self._ingest_infra_topology()
        if include_policy:
            self._ingest_policy_layer()

        graph = TwinGraph()
        for node in self.state.nodes.values():
            graph.add_node(node)
        for edge in self.state.edges.values():
            graph.add_edge(edge)

        layer_counts = {
            layer: sum(1 for node in self.state.nodes.values() if node.layer == layer)
            for layer in ("observed", "desired", "simulated")
        }
        return graph.to_snapshot(
            generated_at=base_map.generated_at,
            window_minutes=minutes,
            meta={
                "include_flows": include_flows and settings.NETWORK_FLOWS_ENABLED,
                "include_policy": include_policy,
                "include_trusttwin": include_trusttwin,
                "trusttwin_devices": trusttwin_count,
                "node_count": len(self.state.nodes),
                "edge_count": len(self.state.edges),
                "layer_counts": layer_counts,
                "builder_version": 1,
            },
        )

    def _upsert_node(self, node: TwinNode) -> None:
        existing = self.state.nodes.get(node.id)
        if existing is None:
            self.state.nodes[node.id] = node
            return
        merged_props = {**existing.properties, **node.properties}
        self.state.nodes[node.id] = existing.model_copy(
            update={
                "label": node.label or existing.label,
                "properties": merged_props,
                "last_seen_at": node.last_seen_at or existing.last_seen_at,
                "first_seen_at": existing.first_seen_at or node.first_seen_at,
                "stale": node.stale,
            }
        )

    def _upsert_edge(
        self,
        *,
        relation: str,
        source_id: str,
        target_id: str,
        layer: TwinLayer,
        weight: float = 1.0,
        properties: Optional[dict] = None,
        bidirectional: bool = False,
    ) -> None:
        eid = edge_id(relation, source_id, target_id)
        props = properties or {}
        existing = self.state.edges.get(eid)
        if existing is None:
            self.state.edges[eid] = TwinEdge(
                id=eid,
                source_id=source_id,
                target_id=target_id,
                relation=relation,  # type: ignore[arg-type]
                layer=layer,
                weight=weight,
                properties=props,
                bidirectional=bidirectional,
            )
            return
        self.state.edges[eid] = existing.model_copy(
            update={
                "weight": existing.weight + weight,
                "properties": {**existing.properties, **props},
            }
        )

    def _ingest_observed_map(self, map_data: NetworkMapResponse) -> None:
        map_nodes = {node.id: node for node in map_data.nodes}
        app_to_device: dict[str, str] = {}
        flow_client_ip: dict[str, str] = {}

        for node in map_data.nodes:
            twin = self._map_node_to_twin(node, map_data.generated_at)
            if twin is not None:
                self._upsert_node(twin)
                if twin.entity_type == "domain":
                    self.state.observed_domains.add(twin.id)

        for edge in map_data.edges:
            if edge.kind == "foreground":
                app_to_device[edge.target] = edge.source

        for edge in map_data.edges:
            if edge.kind == "flow_session":
                client_ip = self._resolve_flow_client_ip(
                    edge.source, map_nodes, app_to_device, flow_client_ip
                )
                if client_ip:
                    flow_client_ip[edge.target] = client_ip
                self._expand_flow_node(edge.target, client_ip, map_data.generated_at)
                relation = "opens" if edge.source.startswith("app:") else "opens_direct"
                flow_nid = self._twin_flow_id(edge.target, client_ip)
                if flow_nid:
                    self._upsert_edge(
                        relation=relation,
                        source_id=edge.source,
                        target_id=flow_nid,
                        layer="observed",
                        weight=float(edge.query_count),
                        properties={"blocked_count": edge.blocked_count},
                    )
                continue

            if edge.kind == "dns_to_flow":
                client_ip = flow_client_ip.get(edge.target)
                self._expand_flow_node(edge.target, client_ip, map_data.generated_at)
                flow_nid = self._twin_flow_id(edge.target, client_ip)
                if flow_nid:
                    self._upsert_edge(
                        relation="correlates",
                        source_id=edge.source,
                        target_id=flow_nid,
                        layer="observed",
                        weight=float(edge.query_count),
                        bidirectional=True,
                    )
                continue

            relation = MAP_EDGE_TO_RELATION.get(edge.kind)
            if relation is None:
                continue
            self._upsert_edge(
                relation=relation,
                source_id=edge.source,
                target_id=edge.target,
                layer="observed",
                weight=float(edge.query_count),
                properties={"blocked_count": edge.blocked_count},
            )

    def _map_node_to_twin(
        self,
        node: NetworkMapNode,
        observed_at: datetime,
    ) -> Optional[TwinNode]:
        if node.type == "flow":
            return None
        entity_type = node.type  # device, app, domain
        props: dict = {}
        if node.app_slug:
            props["app_slug"] = node.app_slug
        if node.client_ip:
            props["client_ip"] = node.client_ip
        if node.device_id is not None:
            props["device_id"] = node.device_id
        if node.blocked is not None:
            props["blocked"] = node.blocked
        if node.fresh is not None:
            props["fresh"] = node.fresh
        return TwinNode(
            id=node.id,
            entity_type=entity_type,  # type: ignore[arg-type]
            layer="observed",
            label=node.label,
            properties=props,
            last_seen_at=observed_at,
            stale=bool(node.fresh is False),
        )

    @staticmethod
    def _resolve_flow_client_ip(
        source_id: str,
        map_nodes: dict[str, NetworkMapNode],
        app_to_device: dict[str, str],
        flow_client_ip: dict[str, str],
    ) -> str:
        if source_id.startswith("device:"):
            node = map_nodes.get(source_id)
            return (node.client_ip or "") if node else ""
        if source_id.startswith("app:"):
            device_nid = app_to_device.get(source_id)
            if not device_nid:
                return ""
            node = map_nodes.get(device_nid)
            return (node.client_ip or "") if node else ""
        return ""

    @staticmethod
    def _parse_map_flow_id(flow_nid: str) -> Optional[tuple[str, str, int]]:
        if not flow_nid.startswith("flow:"):
            return None
        parts = flow_nid.split(":", 3)
        if len(parts) != 4:
            return None
        _prefix, protocol, dest_ip, port_str = parts
        try:
            port = int(port_str)
        except ValueError:
            return None
        return protocol, dest_ip, port

    def _twin_flow_id(self, map_flow_id: str, client_ip: Optional[str]) -> Optional[str]:
        parsed = self._parse_map_flow_id(map_flow_id)
        if parsed is None or not client_ip:
            return None
        protocol, dest_ip, port = parsed
        return flow_session_id(protocol, dest_ip, port, client_ip)

    def _expand_flow_node(
        self,
        map_flow_id: str,
        client_ip: Optional[str],
        observed_at: datetime,
    ) -> None:
        parsed = self._parse_map_flow_id(map_flow_id)
        if parsed is None or not client_ip:
            return
        protocol, dest_ip, port = parsed
        fsid = flow_session_id(protocol, dest_ip, port, client_ip)
        if fsid in self.state.nodes:
            return

        self._upsert_node(
            TwinNode(
                id=fsid,
                entity_type="flow_session",
                layer="observed",
                label=f"{protocol.upper()}/{port} → {dest_ip}",
                properties={
                    "protocol": protocol,
                    "dest_ip": dest_ip,
                    "dest_port": port,
                    "client_ip": client_ip,
                },
                last_seen_at=observed_at,
            )
        )
        l4_nid = l4_service_id(protocol, port)
        self._upsert_node(
            TwinNode(
                id=l4_nid,
                entity_type="l4_service",
                layer="observed",
                label=f"{protocol.upper()} {port}",
                properties={"protocol": protocol, "port": port},
            )
        )
        ip_nid = ip_id(dest_ip)
        self._upsert_node(
            TwinNode(
                id=ip_nid,
                entity_type="ip_address",
                layer="observed",
                label=dest_ip,
                properties={"addr": dest_ip},
            )
        )
        self._upsert_edge(
            relation="uses_service",
            source_id=fsid,
            target_id=l4_nid,
            layer="observed",
        )
        self._upsert_edge(
            relation="destinates",
            source_id=fsid,
            target_id=ip_nid,
            layer="observed",
        )

    def _ingest_flow_resolutions(self, *, minutes: int) -> None:
        flows = list_recent_flows(max_age_sec=max(60, minutes * 60))
        for flow in flows:
            self._ingest_stored_flow_resolution(flow)

    def _ingest_stored_flow_resolution(self, flow: StoredFlow) -> None:
        if not flow.correlated_domain:
            return
        root = extract_root_domain(flow.correlated_domain)
        d_nid = domain_id(root)
        if d_nid not in self.state.nodes:
            self._upsert_node(
                TwinNode(
                    id=d_nid,
                    entity_type="domain",
                    layer="observed",
                    label=root,
                    properties={},
                    last_seen_at=flow.observed_at,
                )
            )
            self.state.observed_domains.add(d_nid)
        ip_nid = ip_id(flow.dest_ip)
        self._upsert_node(
            TwinNode(
                id=ip_nid,
                entity_type="ip_address",
                layer="observed",
                label=flow.dest_ip,
                properties={"addr": flow.dest_ip},
                last_seen_at=flow.observed_at,
            )
        )
        self._upsert_edge(
            relation="resolves_to",
            source_id=d_nid,
            target_id=ip_nid,
            layer="observed",
            properties={"client_ip": flow.client_ip},
        )

    def _ingest_infra_topology(self) -> None:
        infra_labels = {
            "ec2_gateway": "EC2 Gateway",
            "dns_resolver": "TrustEdge DNS",
        }
        for kind, label in infra_labels.items():
            self._upsert_node(
                TwinNode(
                    id=infra_id(kind),
                    entity_type="infra_component",
                    layer="desired",
                    label=label,
                    properties={"kind": kind},
                )
            )
        for source_kind, target_kind, relation in INFRA_CHAIN:
            self._upsert_edge(
                relation=relation,
                source_id=infra_id(source_kind),
                target_id=infra_id(target_kind),
                layer="desired",
            )

    @staticmethod
    def _tt_component_id(device_id: str, kind: str) -> str:
        """Per-device TrustTwin infra node id (stable, graph-unique)."""
        return f"infra:tt:{device_id}:{kind}"

    @staticmethod
    def _tt_port_service_name(port: int) -> str:
        return {
            443: "HTTPS",
            80: "HTTP",
            53: "DNS",
            22: "SSH",
            993: "IMAPS",
            995: "POP3S",
            587: "SMTP",
            853: "DoT",
            5223: "APNs",
            3478: "STUN",
            8443: "HTTPS-alt",
            8080: "HTTP-alt",
            19302: "WebRTC",
            123: "NTP",
        }.get(port, f"TCP/{port}")

    def _ingest_trusttwin(self) -> int:
        """Merge TrustTwin agents for security map: who talked to what.

        Graph (no DNS/remote IPs — TrustTwin privacy contract):
          client → LAN → Internet → remote ports → session aggregates

        Ports hang off Internet (egress), not the client node.
        Host posture stays on device properties only.
        """
        devices = trusttwin_store.list_latest()
        public_net_id = infra_id("public_network")
        if devices:
            self._upsert_node(
                TwinNode(
                    id=public_net_id,
                    entity_type="infra_component",
                    layer="observed",
                    label="Internet",
                    properties={"kind": "public_network", "source": "trusttwin"},
                )
            )

        for rec in devices:
            node_id = trusttwin_store.twin_device_node_id(rec.device_id)
            details = rec.client_details
            network = rec.network_summary
            action = rec.action_summary
            hostname = str(details.get("hostname") or rec.device_id)
            props: dict = {
                "source": "trusttwin",
                "device_id": rec.device_id,
            }
            for key in (
                "hostname",
                "os",
                "os_version",
                "arch",
                "agent_version",
                "timezone",
                "status",
                "uptime_sec",
            ):
                if key in details and details[key] is not None:
                    props[key] = details[key]
            for key in (
                "public_ip",
                "network_type",
                "listening_count",
                "established_count",
                "top_remote_ports",
                "foreground_app_connections",
            ):
                if key in network and network[key] is not None:
                    props[key] = network[key]
            public_ip = network.get("public_ip")
            public_ip_s = str(public_ip).strip() if public_ip is not None else ""
            if public_ip_s and not props.get("client_ip"):
                props["client_ip"] = public_ip_s
            for key in ("presence", "idle_sec", "app_switches"):
                if key in action and action[key] is not None:
                    props[key] = action[key]

            self._upsert_node(
                TwinNode(
                    id=node_id,
                    entity_type="device",
                    layer="observed",
                    label=hostname,
                    properties=props,
                    last_seen_at=rec.last_seen_at,
                    stale=False,
                )
            )

            # Egress path: client → LAN → Internet → public IP.
            net_type = str(network.get("network_type") or "network").strip() or "network"
            lan_label = {
                "wifi": "Wi‑Fi",
                "ethernet": "Ethernet",
                "cellular": "Cellular",
                "wired": "Ethernet",
            }.get(net_type.lower(), net_type.capitalize())
            lan_id = self._tt_component_id(rec.device_id, "tt_lan")
            self._upsert_node(
                TwinNode(
                    id=lan_id,
                    entity_type="infra_component",
                    layer="observed",
                    label=lan_label,
                    properties={
                        "kind": "tt_lan",
                        "source": "trusttwin",
                        "network_type": net_type,
                        "device_id": rec.device_id,
                    },
                    last_seen_at=rec.last_seen_at,
                )
            )
            self._upsert_edge(
                relation="routed_via",
                source_id=node_id,
                target_id=lan_id,
                layer="observed",
                weight=1.0,
                properties={"source": "trusttwin"},
            )
            self._upsert_edge(
                relation="routed_via",
                source_id=lan_id,
                target_id=public_net_id,
                layer="observed",
                weight=1.0,
                properties={"source": "trusttwin"},
            )
            if public_ip_s:
                egress_ip_id = ip_id(public_ip_s)
                self._upsert_node(
                    TwinNode(
                        id=egress_ip_id,
                        entity_type="ip_address",
                        layer="observed",
                        label=public_ip_s,
                        properties={
                            "source": "trusttwin",
                            "role": "public_egress",
                            "addr": public_ip_s,
                        },
                        last_seen_at=rec.last_seen_at,
                    )
                )
                self._upsert_edge(
                    relation="destinates",
                    source_id=public_net_id,
                    target_id=egress_ip_id,
                    layer="observed",
                    weight=1.0,
                    properties={"source": "trusttwin"},
                )

            # Focus apps (processes) for attribution on destinations.
            focus_apps: list[tuple[str, str, str]] = []  # slug, label, node_id
            focus = action.get("focus")
            if isinstance(focus, list):
                for entry in focus:
                    if not isinstance(entry, dict):
                        continue
                    slug = trusttwin_store.app_slug_from_focus(entry)
                    app_label = str(entry.get("app_name") or slug)
                    app_nid = app_id(slug)
                    app_props: dict = {
                        "source": "trusttwin",
                        "app_slug": slug,
                        "app_name": app_label,
                    }
                    if entry.get("bundle_id"):
                        app_props["bundle_id"] = entry["bundle_id"]
                    self._upsert_node(
                        TwinNode(
                            id=app_nid,
                            entity_type="app",
                            layer="observed",
                            label=app_label,
                            properties=app_props,
                            last_seen_at=rec.last_seen_at,
                        )
                    )
                    duration = entry.get("duration_sec")
                    try:
                        weight = float(duration) if duration is not None else 1.0
                    except (TypeError, ValueError):
                        weight = 1.0
                    self._upsert_edge(
                        relation="runs",
                        source_id=node_id,
                        target_id=app_nid,
                        layer="observed",
                        weight=max(weight, 0.0),
                        properties={"source": "trusttwin", "duration_sec": weight},
                    )
                    focus_apps.append((slug, app_label, app_nid))

            # Destinations: remote port aggregates attributed to processes when known.
            client_key = public_ip_s or rec.device_id
            top_ports = network.get("top_remote_ports")
            if not isinstance(top_ports, list):
                continue
            for idx, entry in enumerate(top_ports):
                if not isinstance(entry, dict):
                    continue
                try:
                    port = int(entry.get("port"))
                except (TypeError, ValueError):
                    continue
                if port <= 0 or port > 65535:
                    continue
                try:
                    count = float(entry.get("count") or 1)
                except (TypeError, ValueError):
                    count = 1.0
                count = max(count, 1.0)
                protocol = "tcp"
                service = self._tt_port_service_name(port)

                app_slug = ""
                app_name = str(entry.get("app_name") or "").strip()
                bundle_id = str(entry.get("bundle_id") or "").strip()
                if app_name or bundle_id:
                    app_slug = trusttwin_store.app_slug_from_focus(
                        {"app_name": app_name, "bundle_id": bundle_id}
                    )
                    app_nid = app_id(app_slug)
                    if not app_name:
                        app_name = app_slug
                    self._upsert_node(
                        TwinNode(
                            id=app_nid,
                            entity_type="app",
                            layer="observed",
                            label=app_name,
                            properties={
                                "source": "trusttwin",
                                "app_slug": app_slug,
                                "app_name": app_name,
                                "bundle_id": bundle_id or None,
                            },
                            last_seen_at=rec.last_seen_at,
                        )
                    )
                    self._upsert_edge(
                        relation="runs",
                        source_id=node_id,
                        target_id=app_nid,
                        layer="observed",
                        weight=count,
                        properties={"source": "trusttwin"},
                    )
                elif focus_apps:
                    app_slug, app_name, app_nid = focus_apps[idx % len(focus_apps)]

                # Unique per process+port so Safari:443 and Code:443 both appear.
                flow_token = app_slug.replace(":", "_") if app_slug else "agg"
                l4_nid = l4_service_id(protocol, port)
                flow_nid = flow_session_id(protocol, flow_token, port, client_key)

                self._upsert_node(
                    TwinNode(
                        id=l4_nid,
                        entity_type="l4_service",
                        layer="observed",
                        label=f"{service} :{port}",
                        properties={
                            "protocol": protocol,
                            "port": port,
                            "service": service,
                            "source": "trusttwin",
                        },
                        last_seen_at=rec.last_seen_at,
                    )
                )
                flow_props: dict = {
                    "protocol": protocol,
                    "dest_ip": "*",
                    "dest_port": port,
                    "client_ip": client_key,
                    "source": "trusttwin",
                    "aggregate": True,
                    "connection_count": count,
                    "service": service,
                }
                if app_slug:
                    flow_props["app_slug"] = app_slug
                if app_name:
                    flow_props["app_name"] = app_name
                session_label = (
                    f"{app_name} · {service} ×{int(count)}" if app_name else f"{service} ×{int(count)}"
                )
                self._upsert_node(
                    TwinNode(
                        id=flow_nid,
                        entity_type="flow_session",
                        layer="observed",
                        label=session_label,
                        properties=flow_props,
                        last_seen_at=rec.last_seen_at,
                    )
                )
                # Remote ports hang off Internet egress, not the client node.
                self._upsert_edge(
                    relation="opens_direct",
                    source_id=public_net_id,
                    target_id=flow_nid,
                    layer="observed",
                    weight=count,
                    properties={"source": "trusttwin"},
                )
                self._upsert_edge(
                    relation="uses_service",
                    source_id=flow_nid,
                    target_id=l4_nid,
                    layer="observed",
                    weight=count,
                    properties={"source": "trusttwin"},
                )
        return len(devices)

    def _ingest_policy_layer(self) -> None:
        return
