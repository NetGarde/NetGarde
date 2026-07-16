from __future__ import annotations


def device_id(device_pk: int) -> str:
    return f"device:{device_pk}"


def app_id(slug: str) -> str:
    return f"app:{slug.lower()}"


def domain_id(root_or_fqdn: str) -> str:
    return f"domain:{root_or_fqdn.lower().rstrip('.')}"


def ip_id(addr: str) -> str:
    return f"ip:{addr}"


def l4_service_id(protocol: str, port: int) -> str:
    return f"l4:{protocol.lower()}:{port}"


def flow_session_id(protocol: str, dest_ip: str, dest_port: int, client_ip: str) -> str:
    return f"flow:{protocol.lower()}:{dest_ip}:{dest_port}:{client_ip}"


def infra_id(kind: str) -> str:
    return f"infra:{kind.lower()}"


def edge_id(relation: str, source_id: str, target_id: str) -> str:
    return f"{relation}:{source_id}->{target_id}"
