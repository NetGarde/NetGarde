# System architecture

Component topology and data flows for the TrustEdge **security observability platform** (VPN/DNS visibility, TrustTwin endpoint telemetry, rules-based detection, optional enforcement). For design principles, security model, and implementation patterns, see [DESIGN.md](DESIGN.md).

---

## Architecture diagram

<img width="3840" height="2618" alt="TrustEdge system architecture diagram" src="https://github.com/user-attachments/assets/bab37178-52c4-4f6d-b4ac-1500230d0af5" />

---

## Component overview

| Layer | Components | Role |
|-------|------------|------|
| **Clients** | Site router, laptops, phones | DNS traffic tunneled via WireGuard to EC2 |
| **Endpoint agents** | TrustTwin (`trusttwin`) | Process, app, and network posture telemetry (no VPN) |
| **EC2 host** | WireGuard, dnsmasq, iptables | VPN termination, DNS resolution, traffic blocking |
| **Host services** | `trustedge-wg-agent`, `trustedge-log-watcher` | Peer apply, quarantine iptables, DNS log ingest, trigger policy sync |
| **Docker** | FastAPI backend, dns-sync, detection-engine, trusttwin-api | API, policy computation, dnsmasq config generation, endpoint ingest, rules engine |
| **AWS** | RDS PostgreSQL, S3, CloudFront, ECR | Persistent state, dashboard hosting, image registry |
| **Redis** | Usage samples + TrustTwin live state (EC2) | Real-time VPN throughput; endpoint agent mirror for observability graph |

---

## Data flows

### DNS query path

```
Client → WireGuard → dnsmasq → dnsmasq.log
                              → log_watcher → POST /dns-queries/bulk → Backend
                              → WebSocket → Dashboard (live feed)
                              → RDS (blocked queries only, by default)
```

### Endpoint telemetry path

```
TrustTwin agent → POST /v1/events → trusttwin-api → Redis + Kafka (trusttwin.events)
                 → detection-engine → POST /twin/alerts/ingest → Backend
                 → observability graph + dashboard alerts
```

### Policy enforcement path

```
Dashboard → Backend (policy / quarantine / client block)
         → RDS (source of truth)
         → wg-agent → iptables (quarantine) + run-sync.sh
         → dns-sync → GET /policy/dns-sync → dnsmasq conf → reload dnsmasq
```

### VPN enroll path

```
TrustEdgeClient → POST /v1/enroll → Backend → device + IP allocation
              → wg-agent POST /v1/apply-peer → WireGuard peer on host
              → WireGuard config returned to client
```

---

## Trust boundaries

| Boundary | Why it exists |
|----------|---------------|
| **Docker ↔ EC2 host** | Containers cannot mutate `wg0`, `iptables`, or reload host `dnsmasq` |
| **CloudFront ↔ Backend** | HTTPS termination; API proxied to EC2 :8000 |
| **Token scopes** | Admin, DNS ingest, wg-agent, and device tokens protect different surfaces |

Details: [DESIGN.md § Security model](DESIGN.md#security-model).

---

## Related docs

- [DESIGN.md](DESIGN.md) — full design guide
- [host-agent/README.md](../host-agent/README.md) — host agent setup
- [ENV_SETUP.md](ENV_SETUP.md) — configuration
- [CLOUDWATCH_LOGGING.md](CLOUDWATCH_LOGGING.md) — operational logging
- [TrustEdgeClient](https://github.com/TrustEdge/TrustEdgeClient) — VPN enroll client (separate repo)
