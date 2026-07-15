# <img src="assets/icons/layout.svg" width="28" height="28" align="absmiddle" alt="" /> Screenshot assets

Images referenced by the root [README](../README.md). Prefer captures of **endpoint / detection / alerts** views as the UI evolves.

## Captures

| File | Page / route | What to show | Status |
|------|--------------|--------------|--------|
| `dashboard-home.png` | `/` | Overview, live stats, attack alerts | ✓ (may lag current UI) |
| `client-profiles.png` | device / twin views | Endpoint or alert detail | ✓ |
| `client-map.png` | map views | Observability map | ✓ |

## Capture tips

- **Theme:** Dark mode (default) — matches production UI.
- **Resolution:** ~1400px wide; crop browser chrome if possible.
- **Format:** PNG or WebP; keep each file under ~500 KB.
- **Data:** Use a populated environment (live clients, a few alerts) so screens look active in portfolio context.
- **Privacy:** Redact real IPs, hostnames, or identifiers if the repo is public.

## Optional

- `country-access.png` — `/policy/countries` geo policy editor
