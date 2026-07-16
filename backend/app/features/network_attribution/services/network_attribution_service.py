from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.features.devices.models.device import Device
from app.features.network_attribution.models.device_network_context import DeviceNetworkContext
from app.features.network_attribution.repositories.network_attribution_repository import (
    AppUsageRollupRepository,
    NetworkContextRepository,
)
from app.features.network_attribution.schemas.network_attribution import (
    AppUsageHourlyListResponse,
    AppUsageHourlyRead,
    AppUsageSummaryItem,
    AppUsageSummaryResponse,
    NetworkAttributionReportRequest,
    NetworkAttributionReportResponse,
    NetworkMapEdge,
    NetworkMapNode,
    NetworkMapResponse,
)
from app.features.network_attribution.services.app_catalog import normalize_app
from app.shared.config import settings


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class ResolvedAttribution:
    app_slug: str
    app_display_name: str


class NetworkAttributionService:
    def __init__(self, db: Session):
        self.db = db
        self.rollup_repo = AppUsageRollupRepository(db)
        self.context_repo = NetworkContextRepository(db)

    def ingest(self, device: Device, payload: NetworkAttributionReportRequest) -> NetworkAttributionReportResponse:
        if not settings.NETWORK_ATTRIBUTION_ENABLED:
            return NetworkAttributionReportResponse(stored=False, intervals_received=0)

        latest_observed: Optional[datetime] = None
        latest_slug = ""
        latest_display = ""
        latest_bundle = ""

        for interval in payload.intervals:
            normalized = normalize_app(bundle_id=interval.bundle_id, app_name=interval.app_name)
            self.rollup_repo.add_active_seconds(
                device.id,
                app_slug=normalized.app_slug,
                app_display_name=normalized.app_display_name,
                started_at=interval.started_at,
                duration_sec=interval.duration_sec,
            )
            observed = interval.started_at
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            observed = observed + timedelta(seconds=interval.duration_sec)
            if latest_observed is None or observed >= latest_observed:
                latest_observed = observed
                latest_slug = normalized.app_slug
                latest_display = normalized.app_display_name
                latest_bundle = interval.bundle_id.strip()

        if latest_observed is not None:
            self.context_repo.upsert(
                device.id,
                app_slug=latest_slug,
                app_display_name=latest_display,
                bundle_id=latest_bundle,
                observed_at=latest_observed,
            )

        self.db.commit()
        return NetworkAttributionReportResponse(
            stored=True,
            intervals_received=len(payload.intervals),
        )

    def resolve_attribution(self, device_id: int, query_timestamp: datetime) -> Optional[ResolvedAttribution]:
        if not settings.NETWORK_ATTRIBUTION_ENABLED:
            return None

        ctx = self.context_repo.get(device_id)
        if ctx is None:
            return None

        if query_timestamp.tzinfo is None:
            query_timestamp = query_timestamp.replace(tzinfo=timezone.utc)

        max_age = max(1, int(settings.NETWORK_ATTRIBUTION_MAX_AGE_SEC))
        observed_at = _as_utc(ctx.observed_at)
        age = abs((query_timestamp - observed_at).total_seconds())
        if age > max_age:
            return None

        return ResolvedAttribution(app_slug=ctx.app_slug, app_display_name=ctx.app_display_name)

    def resolve_attribution_for_client_ip(
        self,
        client_ip: str,
        observed_at,
    ) -> Optional[ResolvedAttribution]:
        """No longer resolvable: client IP -> device mapping required VPN leases."""
        return None

    def list_hourly(self, device_id: int, *, hours: int = 168, app_slug: Optional[str] = None) -> AppUsageHourlyListResponse:
        hours = max(1, min(hours, 24 * 30))
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        rollups = self.rollup_repo.list_rollups(device_id, since=since, app_slug=app_slug)
        items = [
            AppUsageHourlyRead(
                window_start=r.window_start,
                hour_utc=r.hour_utc,
                app_slug=r.app_slug,
                app_display_name=r.app_display_name,
                active_seconds=r.active_seconds,
                sample_count=r.sample_count,
                active_minutes=round(r.active_seconds / 60.0, 2),
                usage_share_pct=round((r.active_seconds / 3600.0) * 100.0, 2),
            )
            for r in rollups
        ]
        return AppUsageHourlyListResponse(device_id=device_id, hours=hours, items=items)

    def summarize(self, device_id: int, *, hours: int = 168) -> AppUsageSummaryResponse:
        hours = max(1, min(hours, 24 * 30))
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        rows = self.rollup_repo.summarize(device_id, since=since)
        items = [
            AppUsageSummaryItem(
                app_slug=slug,
                app_display_name=display,
                total_active_seconds=total_sec,
                total_active_hours=round(total_sec / 3600.0, 2),
                hourly_bucket_count=buckets,
                avg_active_minutes_per_hour=round(avg_min, 2),
            )
            for slug, display, total_sec, buckets, avg_min in rows
        ]
        return AppUsageSummaryResponse(device_id=device_id, hours=hours, items=items)

    def build_map(self, *, minutes: int = 1) -> NetworkMapResponse:
        minutes = max(1, min(minutes, 60))
        now = datetime.now(timezone.utc)
        since = now - timedelta(minutes=minutes)
        max_age = max(1, int(settings.NETWORK_ATTRIBUTION_MAX_AGE_SEC))

        if not settings.NETWORK_ATTRIBUTION_ENABLED:
            return NetworkMapResponse(generated_at=now, minutes=minutes, nodes=[], edges=[])

        contexts = (
            self.db.query(DeviceNetworkContext)
            .filter(DeviceNetworkContext.observed_at >= since)
            .all()
        )

        device_rows = self.db.query(Device.id, Device.hostname, Device.external_id).all()
        device_meta: dict[int, tuple[str, str]] = {
            device_id: (hostname or external_id, "") for device_id, hostname, external_id in device_rows
        }

        nodes: dict[str, NetworkMapNode] = {}
        edge_map: dict[tuple[str, str, str], NetworkMapEdge] = {}

        def ensure_device(device_id: int) -> str:
            node_id = f"device:{device_id}"
            if node_id not in nodes:
                label, client_ip = device_meta.get(device_id, (f"Device {device_id}", ""))
                nodes[node_id] = NetworkMapNode(
                    id=node_id,
                    type="device",
                    label=label,
                    client_ip=client_ip or None,
                    device_id=device_id,
                )
            return node_id

        def ensure_app(slug: str, display: str) -> str:
            node_id = f"app:{slug}"
            if node_id not in nodes:
                nodes[node_id] = NetworkMapNode(
                    id=node_id,
                    type="app",
                    label=display,
                    app_slug=slug,
                )
            return node_id

        def add_edge(source: str, target: str, kind: str) -> None:
            key = (source, target, kind)
            edge = edge_map.get(key)
            if edge is None:
                edge_map[key] = NetworkMapEdge(
                    source=source,
                    target=target,
                    kind=kind,
                    query_count=1,
                    blocked_count=0,
                )
                return
            edge_map[key] = edge.model_copy(
                update={"query_count": edge.query_count + 1},
            )

        for ctx in contexts:
            device_node = ensure_device(ctx.device_id)
            app_node = ensure_app(ctx.app_slug, ctx.app_display_name)
            fresh = abs((now - _as_utc(ctx.observed_at)).total_seconds()) <= max_age
            ctx_node = nodes[device_node]
            nodes[device_node] = ctx_node.model_copy(update={"fresh": fresh})
            add_edge(device_node, app_node, "foreground")

        return NetworkMapResponse(
            generated_at=now,
            minutes=minutes,
            nodes=list(nodes.values()),
            edges=list(edge_map.values()),
        )

    def enrich_dns_queries(self, queries: list) -> None:
        """No-op: DNS query enrichment removed with DNS product."""

    @staticmethod
    def get_device_by_external_id(db: Session, external_id: str) -> Optional[Device]:
        return db.query(Device).filter(Device.external_id == external_id.strip()).first()
