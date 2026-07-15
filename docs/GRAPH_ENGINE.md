# <img src="assets/icons/collection.svg" width="28" height="28" align="absmiddle" alt="" /> Security Observability Graph Engine

Canonical **entity / dependency** model for TrustEdge endpoint observability. UI layout modes are **projections** of this graph, not its structure.

Product context: [DESIGN.md](DESIGN.md) · API: [API.md](API.md)

> Scope: devices, apps, processes, network posture, and detection alerts.  
> DNS-domain / VPN-tunnel graph nodes from earlier designs are **out of product scope**.

---

## Problem

Flat `nodes[]` + `edges[]` map payloads rewritten only for column layouts cannot support:

| Capability | Need |
|------------|------|
| Impact analysis | “What depends on this device / alert?” |
| Blast radius | Multi-hop reachability from a seed |
| RCA | Reverse walk from symptom → related entities |
| Simulation overlays | Desired / simulated layers on the same IDs |

The graph engine separates **topology** from **presentation**.

---

## Design principles

1. **Every entity is a node** — devices, apps, processes, IPs, alerts, infra as needed.  
2. **Every dependency is an edge** — typed, directed, indexed both ways.  
3. **Layers** — `observed` (telemetry), `desired` (operator state), `simulated` (what-if).  
4. **Stable IDs** — derived from entity identity, not UI layout.  
5. **Projections are read-only** — map modes filter + layout the canonical graph.  
6. **Time is first-class** — observation windows for recency and RCA.

---

## Primary entity types (endpoint-first)

| Type | Example ID | Typical source |
|------|------------|----------------|
| `device` | `device:{id}` | Agent registration / twin |
| `app` | `app:{slug}` | `action_summary` focus |
| `process` | `proc:{device}:{pid}` | `process_start` / `process_exit` |
| `ip_address` | `ip:{addr}` | `network_summary` / flows |
| `alert` | `alert:{id}` | detection-engine → twin alerts |
| `infra_component` | `infra:{kind}` | Static topology (optional) |

Relation examples: `runs_on`, `focuses`, `connects_to`, `triggered`, `related_to`.

---

## API surface

| Endpoint | Role |
|----------|------|
| `GET /twin/graph/snapshot` | Canonical snapshot |
| `POST /twin/graph/traverse` | Walk from seeds |
| `GET /twin/graph/neighbors` | One-hop expand |

---

## Related

- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)  
- [DESIGN.md](DESIGN.md)  
- [API.md](API.md)  
