# <img src="assets/icons/architecture.svg" width="28" height="28" align="absmiddle" alt="" /> System architecture

Component topology and data flows for the TrustEdge **security observability platform** (TrustEdge Agent endpoint telemetry, rules-based detection, attack alerts). For design principles, security model, and implementation patterns, see [DESIGN.md](DESIGN.md).

---

## <img src="assets/icons/architecture.svg" width="22" height="22" align="absmiddle" alt="" /> Architecture diagram

<p align="center">
  <img width="100%" alt="TrustEdge architecture — endpoint agents, Agent API, Kafka, detection engine, control plane, and dashboard" src="assets/architecture.png" />
</p>

**Primary path:** Endpoint Agent → HTTPS upload → Agent API → Kafka → detection-engine (in-memory alerts + `GET /alerts`) → FastAPI `GET /security/alerts` (proxy) → React dashboard.

---

## <img src="assets/icons/layout.svg" width="22" height="22" align="absmiddle" alt="" /> Component overview

| Layer | Components | Role |
|-------|------------|------|
| **Endpoint agents** | TrustEdge Agent (`trustedge-agent`) | Process, activity, network posture, and AI tools inventory telemetry |
| **Docker** | FastAPI backend, detection-engine, trustedge-agent-api | API, alerts, endpoint ingest, rules engine |
| **AWS** | RDS PostgreSQL, S3, CloudFront, ECR | Persistent state, dashboard hosting, image registry |
| **Redis** | Optional live agent keys (EC2) | Connected-agent APIs / overview helpers |
| **Kafka / Redpanda** | Agent event bus | Detection-engine input stream |

---

## <img src="assets/icons/flow.svg" width="22" height="22" align="absmiddle" alt="" /> Data flows

### Endpoint telemetry path

```
TrustEdge Agent → POST /v1/events → trustedge-agent-api → Kafka (trustedge.agent.events)
                 → detection-engine → POST /security/alerts/ingest → Backend
                 → Agent-API upsert → Postgres agents registry → dashboard Agents
```

### L4 flow ingest (optional)

```
Host conntrack watcher → POST /network-flows/bulk → Backend Redis window → GET /network-flows/live
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
