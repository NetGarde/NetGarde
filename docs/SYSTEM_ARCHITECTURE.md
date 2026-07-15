# <img src="assets/icons/architecture.svg" width="28" height="28" align="absmiddle" alt="" /> System architecture

Component topology and data flows for TrustEdge as an **endpoint security observability** platform: TrustEdge Agent telemetry, ingest API, stream, rules-based detection, and operator alerts.

For design principles and implementation patterns, see [DESIGN.md](DESIGN.md).

---

## <img src="assets/icons/flow.svg" width="22" height="22" align="absmiddle" alt="" /> High-level pipeline

<p align="center">
  <img src="assets/pipeline.svg" alt="Endpoint → Collector → Batch → Compress → Secure upload → Agent API → Stream → Detection Attack → Alert" width="920" />
</p>

| Stage | Where | Role |
|-------|-------|------|
| **Endpoint** | Device | Laptop / workstation running the agent |
| **Collector → Batch → Compress** | [TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) | Gather signals, durable queue, optional zstd |
| **Secure upload** | Agent → HTTPS | Device bearer token |
| **Agent API** | [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) | Register, validate, persist |
| **Stream** | Kafka / Redpanda | `trustedge.agent.events` |
| **Detection Attack** | `detection-engine/` | Rules on process / network patterns |
| **Alert** | TrustEdge backend + UI | Store findings, show operators |

---

## <img src="assets/icons/layout.svg" width="22" height="22" align="absmiddle" alt="" /> Component overview

| Layer | Components | Role |
|-------|------------|------|
| **Endpoints** | TrustEdge Agent (`trustedge-agent`) | Process, app, network, device posture |
| **Ingest** | `trustedge-agent-api` | Auth, batch ingest, optional Kafka publish |
| **Stream** | Kafka / Redpanda | Durable event bus for detection |
| **Detection** | `detection-engine` | Rules consumer → alert ingest |
| **Control plane** | FastAPI backend | Twin graph, alerts API, admin |
| **UI** | React dashboard (S3 / CloudFront) | Operators view posture and attack alerts |
| **Data** | PostgreSQL (RDS), Redis, ECR | Persistent state, live mirrors, images |

---

## <img src="assets/icons/flow.svg" width="22" height="22" align="absmiddle" alt="" /> Data flows

### Endpoint telemetry path

```text
TrustEdge Agent
  → POST /v1/events (Agent API)
  → Redis mirror (optional) + Kafka topic trustedge.agent.events
  → detection-engine (rules)
  → POST /twin/alerts/ingest (TrustEdge backend)
  → Dashboard attack alerts + observability graph
```

### Operator path

```text
Dashboard → Backend REST API → RDS (alerts, devices, twin state)
```

---

## <img src="assets/icons/lock.svg" width="22" height="22" align="absmiddle" alt="" /> Trust boundaries

| Boundary | Why it exists |
|----------|---------------|
| **Endpoint ↔ Agent API** | Device registration + bearer tokens on ingest |
| **CloudFront ↔ Backend** | HTTPS termination; API proxied to the app host |
| **Detection ↔ Backend** | Alert ingest is a controlled write path into RDS |

Details: [DESIGN.md](DESIGN.md).

---

## <img src="assets/icons/layout.svg" width="22" height="22" align="absmiddle" alt="" /> Related docs

- [DESIGN.md](DESIGN.md) — design guide  
- [ENV_SETUP.md](ENV_SETUP.md) — configuration  
- [CLOUDWATCH_LOGGING.md](CLOUDWATCH_LOGGING.md) — operational logging  
- [TrustEdge-Agent](https://github.com/TrustEdgeOrg/TrustEdge-Agent) — endpoint collector  
- [TrustEdge-Agent-API](https://github.com/TrustEdgeOrg/TrustEdge-Agent-API) — ingest API  
