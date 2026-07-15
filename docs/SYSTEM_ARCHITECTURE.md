# <img src="assets/icons/architecture.svg" width="28" height="28" align="absmiddle" alt="" /> System architecture

Component topology and data flows for the TrustEdge **security observability platform** (TrustEdge Agent endpoint telemetry, rules-based detection, WireGuard enrollment, optional quarantine). For design principles, security model, and implementation patterns, see [DESIGN.md](DESIGN.md).

---

## <img src="assets/icons/architecture.svg" width="22" height="22" align="absmiddle" alt="" /> Architecture diagram

<p align="center">
  <img width="100%" alt="TrustEdge architecture — endpoint agents, Agent API, Kafka, detection engine, control plane, and dashboard" src="assets/architecture.svg" />
</p>

**Primary path:** Endpoint Agent → HTTPS upload → Agent API → Kafka → detection-engine → `/twin/alerts/ingest` → FastAPI → React dashboard.

**Optional path:** TrustEdgeClient enroll → WireGuard peer apply via `trustedge-wg-agent` → usage / quarantine on the EC2 host.

---

## <img src="assets/icons/layout.svg" width="22" height="22" align="absmiddle" alt="" /> Component overview

| Layer | Components | Role |
|-------|------------|------|
| **Endpoint agents** | TrustEdge Agent (`trustedge-agent`) | Process, app, and network posture telemetry |
| **VPN clients** | TrustEdgeClient / enrolled peers | WireGuard tunnel; usage and app-focus reports |
| **EC2 host** | WireGuard, iptables | VPN termination, quarantine drops |
| **Host services** | `trustedge-wg-agent` | Peer apply, quarantine iptables |
| **Docker** | FastAPI backend, detection-engine, trustedge-agent-api | API, twin/alerts, endpoint ingest, rules engine |
| **AWS** | RDS PostgreSQL, S3, CloudFront, ECR | Persistent state, dashboard hosting, image registry |
| **Redis** | Usage samples + TrustEdge Agent live state (EC2) | Real-time VPN throughput; endpoint agent mirror for observability graph |
| **Kafka / Redpanda** | Agent event bus | Detection-engine input stream |

---

## <img src="assets/icons/flow.svg" width="22" height="22" align="absmiddle" alt="" /> Data flows

### Endpoint telemetry path

```
TrustEdge Agent → POST /v1/events → trustedge-agent-api → Redis + Kafka (trustedge.agent.events)
                 → detection-engine → POST /twin/alerts/ingest → Backend
                 → observability graph + dashboard alerts
```

### VPN enroll path

```
TrustEdgeClient → POST /v1/enroll → Backend → device + IP allocation
              → wg-agent POST /v1/apply-peer → WireGuard peer on host
              → WireGuard config returned to client
```

### Quarantine path

```
Dashboard → Backend (device quarantine)
         → RDS (source of truth)
         → wg-agent → iptables drop for client IP
```

### Network map path

```
Foreground app reports (POST /v1/network-attribution)
  + optional L4 flow samples (POST /network-flows/bulk)
  → Backend → GET /network-attribution/map → Dashboard
```

---

## <img src="assets/icons/lock.svg" width="22" height="22" align="absmiddle" alt="" /> Trust boundaries

| Boundary | Why it exists |
|----------|---------------|
| **Docker ↔ EC2 host** | Containers cannot mutate `wg0` or `iptables` |
| **CloudFront ↔ Backend** | HTTPS termination; API proxied to EC2 :8000 |
| **Token scopes** | Admin, ingest, wg-agent, and device tokens protect different surfaces |

Details: [DESIGN.md § Security model](DESIGN.md#security-model).

---

## <img src="assets/icons/layout.svg" width="22" height="22" align="absmiddle" alt="" /> Related docs

- [DESIGN.md](DESIGN.md) — full design guide
- [host-agent/README.md](../host-agent/README.md) — host agent setup
- [ENV_SETUP.md](ENV_SETUP.md) — configuration
- [CLOUDWATCH_LOGGING.md](CLOUDWATCH_LOGGING.md) — operational logging
- [TrustEdgeClient](https://github.com/TrustEdgeOrg/TrustEdgeClient) — VPN enroll client (separate repo)
