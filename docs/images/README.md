# <img src="assets/icons/layout.svg" width="28" height="28" align="absmiddle" alt="" /> Screenshot assets

Images referenced by the root [README](../README.md). Use these filenames so links resolve on GitHub.

## Captures

| File | Page / route | What to show | Status |
|------|--------------|--------------|--------|
| `dashboard-home.png` | `/` | Network overview card, AI summary, stats, alerts | ✓ |
| `dashboard-live.png` | `/` | Live throughput chart, DNS live feed, or live clients panel | pending |
| `policy.png` | `/policy` | Policy packs list and device profile assignments | pending |
| `client-profiles.png` | `/client-profiles` | Device detail — behavior score, baseline, quarantine | ✓ |
| `client-map.png` | `/client-map` | World map with enrolled clients | ✓ |
| `blocked-clients.png` | `/blocked-clients` | Quarantined and DNS-blocked devices table | pending |

## Capture tips

- **Theme:** Dark mode (default) — matches production UI.
- **Resolution:** ~1400px wide; crop browser chrome if possible.
- **Format:** PNG or WebP; keep each file under ~500 KB.
- **Data:** Use a populated environment (live clients, a few alerts) so screens look active in portfolio context.
- **Privacy:** Redact real IPs, hostnames, or identifiers if the repo is public.

## Optional

- `country-access.png` — `/policy/countries` geo policy editor
