#!/usr/bin/env python3
"""Seed VPN clients, DNS destinations, apps, and L4 flows for a full Network map.

Requires TrustEdge API stack (Postgres + Redis). Example:

  cd /Users/eladmines/Desktop/TrustEdge
  make dev-up
  python3 scripts/seed_network_map_demo.py

Then open the dashboard Network map.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env.dev")
    load_dotenv(BACKEND / ".env")
except ImportError:
    pass

os.environ.setdefault(
    "DB_URL",
    "postgresql+psycopg2://postgres:trustedge@127.0.0.1:5432/trustedge",
)
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
os.environ.setdefault("USAGE_REDIS_ENABLED", "true")

from sqlalchemy.orm import Session  # noqa: E402

from app.features.policy.models.policy_pack import PolicyPack  # noqa: E402, F401
from app.features.policy.models.policy_profile import PolicyProfile  # noqa: E402, F401
from app.features.devices.models.device import Device  # noqa: E402
from app.features.dns_queries.models.dns_query import DnsQuery  # noqa: E402
from app.features.network_attribution.models.device_network_context import (  # noqa: E402
    DeviceNetworkContext,
)
from app.features.network_flows.schemas.network_flow import (  # noqa: E402
    DnsResolutionCreate,
    NetworkFlowCreate,
)
from app.features.network_flows.services import flow_store  # noqa: E402
from app.features.vpn.models.ip_lease import IpLease  # noqa: E402
from app.features.vpn.models.ip_pool import IpPool  # noqa: E402
from app.features.vpn.models.vpn_peer import VpnPeer  # noqa: E402
from app.shared.database import SessionLocal  # noqa: E402
from app.shared.redis_client import close_redis, redis_available  # noqa: E402

DEMO_SOURCE = "map_demo"
POOL_NAME = "map-demo-pool"

# dns: (domain, blocked, app_slug, app_display)
# flows: (dest_ip, dest_port, domain|None, app_slug, app_display)
FLEET = [
    {
        "device_id": "vpn-laptop-elad",
        "hostname": "elad-vpn-laptop",
        "ip": "10.0.0.12",
        "mac": "aa:bb:cc:dd:ee:01",
        "app_slug": "slack",
        "app_display": "Slack",
        "bundle_id": "com.tinyspeck.slackmacgap",
        "dns": [
            ("api.slack.com", False, "slack", "Slack"),
            ("wss-primary.slack.com", False, "slack", "Slack"),
            ("files.slack.com", False, "slack", "Slack"),
            ("github.com", False, "vscode", "Code"),
            ("api.github.com", False, "vscode", "Code"),
            ("objects.githubusercontent.com", False, "vscode", "Code"),
            ("registry.npmjs.org", False, "vscode", "Code"),
            ("malware.example", True, "safari", "Safari"),
            ("ads.tracker.example", True, "safari", "Safari"),
            ("phishing-login.example", True, "safari", "Safari"),
            ("zoom.us", False, "zoom", "Zoom"),
            ("cloudfront.net", False, "zoom", "Zoom"),
            ("openai.com", False, "safari", "Safari"),
            ("chat.openai.com", False, "safari", "Safari"),
        ],
        "flows": [
            ("3.5.1.10", 443, "api.slack.com", "slack", "Slack"),
            ("3.5.1.11", 443, "wss-primary.slack.com", "slack", "Slack"),
            ("140.82.112.4", 443, "github.com", "vscode", "Code"),
            ("140.82.113.5", 443, "api.github.com", "vscode", "Code"),
            ("104.16.0.35", 443, "registry.npmjs.org", "vscode", "Code"),
            ("3.7.2.20", 443, "zoom.us", "zoom", "Zoom"),
            ("104.18.32.7", 443, "chat.openai.com", "safari", "Safari"),
            ("185.1.2.3", 4444, None, "safari", "Safari"),
        ],
    },
    {
        "device_id": "vpn-phone-maya",
        "hostname": "maya-iphone",
        "ip": "10.0.0.18",
        "mac": "aa:bb:cc:dd:ee:02",
        "app_slug": "safari",
        "app_display": "Safari",
        "bundle_id": "com.apple.mobilesafari",
        "dns": [
            ("www.apple.com", False, "safari", "Safari"),
            ("icloud.com", False, "safari", "Safari"),
            ("gsp-ssl.ls.apple.com", False, "safari", "Safari"),
            ("maps.googleapis.com", False, "safari", "Safari"),
            ("instagram.com", False, "safari", "Safari"),
            ("cdninstagram.com", False, "safari", "Safari"),
            ("badphish.example", True, "safari", "Safari"),
            ("crypto-drain.example", True, "safari", "Safari"),
        ],
        "flows": [
            ("17.253.144.10", 443, "www.apple.com", "safari", "Safari"),
            ("17.248.190.1", 443, "icloud.com", "safari", "Safari"),
            ("142.250.185.10", 443, "maps.googleapis.com", "safari", "Safari"),
            ("157.240.3.35", 443, "instagram.com", "safari", "Safari"),
            ("157.240.3.36", 443, "cdninstagram.com", "safari", "Safari"),
        ],
    },
    {
        "device_id": "vpn-desktop-ops",
        "hostname": "ops-desktop",
        "ip": "10.0.0.24",
        "mac": "aa:bb:cc:dd:ee:03",
        "app_slug": "google_chrome",
        "app_display": "Google Chrome",
        "bundle_id": "com.google.Chrome",
        "dns": [
            ("docs.google.com", False, "google_chrome", "Google Chrome"),
            ("drive.google.com", False, "google_chrome", "Google Chrome"),
            ("sheets.google.com", False, "google_chrome", "Google Chrome"),
            ("teams.microsoft.com", False, "microsoft_teams", "Microsoft Teams"),
            ("login.microsoftonline.com", False, "microsoft_teams", "Microsoft Teams"),
            ("outlook.office.com", False, "microsoft_teams", "Microsoft Teams"),
            ("coin-miner.example", True, "google_chrome", "Google Chrome"),
            ("c2-beacon.example", True, "google_chrome", "Google Chrome"),
        ],
        "flows": [
            ("142.250.185.78", 443, "docs.google.com", "google_chrome", "Google Chrome"),
            ("142.250.185.94", 443, "drive.google.com", "google_chrome", "Google Chrome"),
            ("52.109.8.20", 443, "teams.microsoft.com", "microsoft_teams", "Microsoft Teams"),
            ("13.107.42.12", 443, "login.microsoftonline.com", "microsoft_teams", "Microsoft Teams"),
            ("52.96.40.10", 443, "outlook.office.com", "microsoft_teams", "Microsoft Teams"),
        ],
    },
    {
        "device_id": "vpn-tablet-dan",
        "hostname": "dan-ipad",
        "ip": "10.0.0.31",
        "mac": "aa:bb:cc:dd:ee:04",
        "app_slug": "safari",
        "app_display": "Safari",
        "bundle_id": "com.apple.mobilesafari",
        "dns": [
            ("netflix.com", False, "safari", "Safari"),
            ("nflxvideo.net", False, "safari", "Safari"),
            ("spotify.com", False, "safari", "Safari"),
            ("audio-fa.scdn.co", False, "safari", "Safari"),
            ("adware-push.example", True, "safari", "Safari"),
        ],
        "flows": [
            ("54.230.12.10", 443, "netflix.com", "safari", "Safari"),
            ("54.230.12.11", 443, "nflxvideo.net", "safari", "Safari"),
            ("35.186.224.25", 443, "spotify.com", "safari", "Safari"),
        ],
    },
    {
        "device_id": "vpn-win-finance",
        "hostname": "finance-win11",
        "ip": "10.0.0.40",
        "mac": "aa:bb:cc:dd:ee:05",
        "app_slug": "msedge",
        "app_display": "Microsoft Edge",
        "bundle_id": "msedge",
        "dns": [
            ("portal.office.com", False, "msedge", "Microsoft Edge"),
            ("excel.office.com", False, "msedge", "Microsoft Edge"),
            ("teams.microsoft.com", False, "microsoft_teams", "Microsoft Teams"),
            ("outlook.office.com", False, "outlook", "Outlook"),
            ("bank-phish.example", True, "msedge", "Microsoft Edge"),
        ],
        "flows": [
            ("13.107.6.156", 443, "portal.office.com", "msedge", "Microsoft Edge"),
            ("52.109.8.20", 443, "teams.microsoft.com", "microsoft_teams", "Microsoft Teams"),
            ("52.96.40.10", 443, "outlook.office.com", "outlook", "Outlook"),
        ],
    },
    {
        "device_id": "vpn-android-noa",
        "hostname": "noa-pixel",
        "ip": "10.0.0.45",
        "mac": "aa:bb:cc:dd:ee:06",
        "app_slug": "chrome",
        "app_display": "Chrome",
        "bundle_id": "com.android.chrome",
        "dns": [
            ("youtube.com", False, "chrome", "Chrome"),
            ("googlevideo.com", False, "chrome", "Chrome"),
            ("whatsapp.com", False, "whatsapp", "WhatsApp"),
            ("g.whatsapp.net", False, "whatsapp", "WhatsApp"),
            ("apk-malware.example", True, "chrome", "Chrome"),
        ],
        "flows": [
            ("142.250.185.110", 443, "youtube.com", "chrome", "Chrome"),
            ("157.240.20.60", 443, "whatsapp.com", "whatsapp", "WhatsApp"),
            ("157.240.20.61", 5222, "g.whatsapp.net", "whatsapp", "WhatsApp"),
        ],
    },
]


def _ensure_pool(db: Session) -> IpPool:
    pool = db.query(IpPool).filter(IpPool.name == POOL_NAME).first()
    if pool:
        return pool
    pool = IpPool(
        name=POOL_NAME,
        cidr="10.0.0.0/24",
        gateway_ip="10.0.0.1",
        dns_ip="10.0.0.1",
        endpoint="127.0.0.1:51820",
        server_public_key="demo-server-pubkey",
    )
    db.add(pool)
    db.flush()
    return pool


def _upsert_device(db: Session, pool: IpPool, spec: dict, now: datetime) -> tuple[Device, IpLease]:
    peer = db.query(VpnPeer).filter(VpnPeer.device_id == spec["device_id"]).first()
    if peer is None:
        peer = VpnPeer(
            device_id=spec["device_id"],
            public_key=f"demo-pubkey-{spec['device_id']}",
            pool_id=pool.id,
        )
        db.add(peer)
        db.flush()

    lease = (
        db.query(IpLease)
        .filter(IpLease.peer_id == peer.id, IpLease.released_at.is_(None))
        .first()
    )
    if lease is None:
        lease = IpLease(pool_id=pool.id, peer_id=peer.id, ip=spec["ip"])
        db.add(lease)
        db.flush()
    else:
        lease.ip = spec["ip"]

    device = db.query(Device).filter(Device.ip_lease_id == lease.id).first()
    if device is None:
        device = Device(
            ip_lease_id=lease.id,
            hostname=spec["hostname"],
            mac_address=spec["mac"],
            source=DEMO_SOURCE,
            created_at=now,
            updated_at=now,
        )
        db.add(device)
        db.flush()
    else:
        device.hostname = spec["hostname"]
        device.mac_address = spec["mac"]
        device.source = DEMO_SOURCE
        device.updated_at = now
    return device, lease


def _seed_context(db: Session, device: Device, spec: dict, now: datetime) -> None:
    row = db.query(DeviceNetworkContext).filter(DeviceNetworkContext.device_id == device.id).first()
    if row is None:
        db.add(
            DeviceNetworkContext(
                device_id=device.id,
                app_slug=spec["app_slug"],
                app_display_name=spec["app_display"],
                bundle_id=spec.get("bundle_id"),
                observed_at=now,
                updated_at=now,
            )
        )
    else:
        row.app_slug = spec["app_slug"]
        row.app_display_name = spec["app_display"]
        row.bundle_id = spec.get("bundle_id")
        row.observed_at = now
        row.updated_at = now


def _seed_dns(db: Session, lease: IpLease, rows: list, now: datetime) -> int:
    db.query(DnsQuery).filter(DnsQuery.client_ip == lease.ip).delete()
    count = 0
    for i, (domain, blocked, slug, display) in enumerate(rows):
        db.add(
            DnsQuery(
                timestamp=now - timedelta(seconds=i * 2),
                client_ip=lease.ip,
                domain=domain,
                query_type="A",
                action="blocked" if blocked else "forwarded",
                blocked=blocked,
                attributed_app_slug=slug,
                attributed_app_display_name=display,
            )
        )
        count += 1
    return count


def _seed_flows(spec: dict, now: datetime) -> int:
    flows: list[NetworkFlowCreate] = []
    resolutions: list[DnsResolutionCreate] = []
    correlated: dict[str, str | None] = {}
    attribution: dict[str, tuple[str | None, str | None]] = {}

    for i, (dest_ip, dest_port, domain, slug, display) in enumerate(spec["flows"]):
        flow = NetworkFlowCreate(
            observed_at=now - timedelta(seconds=i * 2),
            client_ip=spec["ip"],
            protocol="tcp",
            src_port=50000 + i,
            dest_ip=dest_ip,
            dest_port=dest_port,
            state="ESTABLISHED",
        )
        flows.append(flow)
        key = flow_store.flow_dedupe_key(flow)
        correlated[key] = domain
        attribution[spec["ip"]] = (slug, display)
        if domain:
            resolutions.append(
                DnsResolutionCreate(
                    timestamp=now - timedelta(seconds=i * 2 + 1),
                    client_ip=spec["ip"],
                    domain=domain,
                    resolved_ip=dest_ip,
                )
            )

    flow_store.record_resolutions(resolutions)
    return flow_store.record_flows(flows, correlated_domains=correlated, attribution=attribution)


def main() -> int:
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        pool = _ensure_pool(db)
        dns_total = 0
        flow_total = 0
        for spec in FLEET:
            device, lease = _upsert_device(db, pool, spec, now)
            _seed_context(db, device, spec, now)
            dns_total += _seed_dns(db, lease, spec["dns"], now)
            db.commit()
            flow_total += _seed_flows(spec, now)
            print(f"seeded VPN client {spec['hostname']} ({spec['ip']}) id={device.id}")

        print(
            f"done: {len(FLEET)} clients, {dns_total} DNS rows, {flow_total} flows "
            f"(redis={'on' if redis_available() else 'off'})"
        )
        print("Open Network map and refresh.")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()
        close_redis()


if __name__ == "__main__":
    raise SystemExit(main())
