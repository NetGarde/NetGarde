# <img src="assets/icons/architecture.svg" width="28" height="28" align="absmiddle" alt="" /> System architecture

Component topology and data flows for the TrustEdge **security observability platform** (TrustEdge Agent endpoint telemetry, rules-based detection, attack alerts). For design principles, security model, and implementation patterns, see [DESIGN.md](DESIGN.md).

---

## <img src="assets/icons/architecture.svg" width="22" height="22" align="absmiddle" alt="" /> Architecture diagram

<p align="center">
  <img width="100%" alt="TrustEdge architecture — endpoint agents, Agent API, Kafka, detection engine, control plane, and dashboard" src="assets/architecture.png" />
</p>

**Primary path:** Endpoint Agent → HTTPS upload → Agent API → Kafka → detection-engine → alerts ingest (`/security/alerts/ingest`) → FastAPI → React dashboard.

---

## <img src="assets/icons/layout.svg" width="22" height="22" align="absmiddle" alt="" /> Component overview

| Layer | Components | Role |
|-------|------------|------|
| **Endpoint agents** | TrustEdge Agent (`trustedge-agent`) | Process, app, and network posture telemetry |
| **Docker** | FastAPI backend, detection-engine, trustedge-agent-api | API, alerts, endpoint ingest, rules engine |
| **AWS** | RDS PostgreSQL, S3, CloudFront, ECR | Persistent state, dashboard hosting, image registry |
| **Redis** | TrustEdge Agent live state (EC2) | Endpoint agent mirror for observability graph |
| **Kafka / Redpanda** | Agent event bus | Detection-engine input stream |

---

## <img src="assets/icons/flow.svg" width="22" height="22" align="absmiddle" alt="" /> Data flows

### Endpoint telemetry path

```
TrustEdge Agent → POST /v1/events → trustedge-agent-api → Redis + Kafka (trustedge.agent.events)
                 → detection-engine → POST /security/alerts/ingest → Backend
                 → observability graph + dashboard alerts
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
| **CloudFront ↔ Backend** | HTTPS termination; API proxied to EC2 :8000 |
| **Token scopes** | Admin, ingest, and device tokens protect different surfaces |

Details: [DESIGN.md § Security model](DESIGN.md#security-model).

---

## <img src="assets/icons/layout.svg" width="22" height="22" align="absmiddle" alt="" /> Related docs

- [DESIGN.md](DESIGN.md) — full design guide
- [ENV_SETUP.md](ENV_SETUP.md) — configuration
- [CLOUDWATCH_LOGGING.md](CLOUDWATCH_LOGGING.md) — operational logging
