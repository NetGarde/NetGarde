import { useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import { alpha, useTheme } from '@mui/material/styles';
import StreamIcon from '@mui/icons-material/Stream';
import StorageOutlinedIcon from '@mui/icons-material/StorageOutlined';
import FilterAltOutlinedIcon from '@mui/icons-material/FilterAltOutlined';
import RuleOutlinedIcon from '@mui/icons-material/RuleOutlined';
import AccountTreeOutlinedIcon from '@mui/icons-material/AccountTreeOutlined';
import FingerprintOutlinedIcon from '@mui/icons-material/FingerprintOutlined';
import NotificationsActiveOutlinedIcon from '@mui/icons-material/NotificationsActiveOutlined';
import DashboardOutlinedIcon from '@mui/icons-material/DashboardOutlined';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import BlockOutlinedIcon from '@mui/icons-material/BlockOutlined';
import type { ReactElement } from 'react';
import './AgentFlow.css';

type FlowStep = {
  id: string;
  title: string;
  plain: string;
  detail: string;
  icon: ReactElement;
  tone: 'edge' | 'path' | 'cloud' | 'detect';
};

const STEPS: FlowStep[] = [
  {
    id: 'arrive',
    title: 'Events arrive',
    plain: 'Telemetry lands on a durable Kafka topic after the Agent API accepts a batch.',
    detail:
      'The detection engine is a Kafka consumer on trustedge.agent.events. Each message is one agent event: process start, network summary, persistence change, and more.',
    icon: <StreamIcon fontSize="small" />,
    tone: 'cloud',
  },
  {
    id: 'remember',
    title: 'Per-device memory',
    plain: 'Every device gets a short rolling history so rules can compare “now” to “a moment ago.”',
    detail:
      'StateStore keeps roughly the last 100 events (about 30 minutes) per device_id. That’s how parent shells, previous IPs, and bursts become visible.',
    icon: <StorageOutlinedIcon fontSize="small" />,
    tone: 'cloud',
  },
  {
    id: 'lane',
    title: 'Pick a rule lane',
    plain: 'Only the rules that match this event type run — plus one always-on volume check.',
    detail:
      'process_start → process rules. network_summary → network rules. driver/service/persistence → security rules. Any event can also raise event_burst.',
    icon: <FilterAltOutlinedIcon fontSize="small" />,
    tone: 'path',
  },
  {
    id: 'evaluate',
    title: 'Evaluate rules',
    plain: 'Deterministic checks look for attack patterns and drift — no AI verdict.',
    detail:
      'Examples: shell spawning curl, binaries from /tmp, process creation storms, public IP changes, LaunchAgent persistence. If nothing matches, no alert.',
    icon: <RuleOutlinedIcon fontSize="small" />,
    tone: 'detect',
  },
  {
    id: 'evidence',
    title: 'Attach evidence',
    plain: 'Alerts carry enough context for an operator to investigate quickly.',
    detail:
      'Process alerts add ancestry or burst samples into detail. Network alerts include from/to IPs or counts. The UI uses this for graphs and explain.',
    icon: <AccountTreeOutlinedIcon fontSize="small" />,
    tone: 'detect',
  },
  {
    id: 'dedupe',
    title: 'Deduplicate',
    plain: 'The same finding should not spam the console every few seconds.',
    detail:
      'Each alert has a fingerprint. Recently seen fingerprints are skipped. Many windowed rules also have cooldowns (minutes) so noise stays controlled.',
    icon: <FingerprintOutlinedIcon fontSize="small" />,
    tone: 'path',
  },
  {
    id: 'store',
    title: 'Remember alerts',
    plain: 'Fresh alerts are kept in a recent in-memory ring for the dashboard to query.',
    detail:
      'About the last 1000 alerts live in process memory and are served from GET /alerts with filters for device, severity, and type.',
    icon: <NotificationsActiveOutlinedIcon fontSize="small" />,
    tone: 'detect',
  },
  {
    id: 'surface',
    title: 'Show in TrustEdge',
    plain: 'The control plane proxies those alerts into Alerts and agent detail views.',
    detail:
      'Optional AI explain only narrates what rules already fired — it never decides what is malicious.',
    icon: <DashboardOutlinedIcon fontSize="small" />,
    tone: 'detect',
  },
];

const COVERS = [
  'Process chains (shell → downloader, temp-path exec, bursts)',
  'Network drift (IP/type change, flapping, connection spikes)',
  'Security lifecycle (drivers, services, persistence)',
  'Coverage gaps (missing network telemetry, idle with activity)',
];

const NOT_THIS = [
  'Not antivirus signatures or a malware sandbox',
  'Not an LLM deciding “good” vs “bad”',
  'Not long-term alert storage by itself (in-memory ring)',
  'Not a replacement for your full SIEM history',
];

function toneColor(
  tone: FlowStep['tone'],
  theme: ReturnType<typeof useTheme>,
): { bg: string; fg: string; ring: string } {
  const isDark = theme.palette.mode === 'dark';
  switch (tone) {
    case 'edge':
      return {
        bg: alpha(theme.palette.info.main, isDark ? 0.18 : 0.12),
        fg: isDark ? theme.palette.info.light : theme.palette.info.dark,
        ring: alpha(theme.palette.info.main, 0.45),
      };
    case 'path':
      return {
        bg: alpha(theme.palette.primary.main, isDark ? 0.18 : 0.1),
        fg: isDark ? theme.palette.primary.light : theme.palette.primary.dark,
        ring: alpha(theme.palette.primary.main, 0.45),
      };
    case 'cloud':
      return {
        bg: alpha(theme.palette.secondary.main, isDark ? 0.2 : 0.12),
        fg: isDark ? theme.palette.secondary.light : theme.palette.secondary.dark,
        ring: alpha(theme.palette.secondary.main, 0.45),
      };
    case 'detect':
    default:
      return {
        bg: alpha(theme.palette.warning.main, isDark ? 0.18 : 0.14),
        fg: isDark ? theme.palette.warning.light : theme.palette.warning.dark,
        ring: alpha(theme.palette.warning.main, 0.5),
      };
  }
}

export default function DetectionFlow() {
  const theme = useTheme();
  const [activeId, setActiveId] = useState(STEPS[0].id);
  const active = useMemo(
    () => STEPS.find((s) => s.id === activeId) || STEPS[0],
    [activeId],
  );
  const activeTone = toneColor(active.tone, theme);

  return (
    <Box className="agent-flow" sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Paper
        variant="outlined"
        className="agent-flow-hero"
        sx={{
          p: { xs: 2.5, md: 3.5 },
          mb: 3,
          overflow: 'hidden',
          position: 'relative',
          background: (t) =>
            `linear-gradient(135deg, ${alpha(t.palette.warning.main, t.palette.mode === 'dark' ? 0.14 : 0.1)} 0%, ${alpha(
              t.palette.background.paper,
              0.4,
            )} 55%, ${alpha(t.palette.primary.main, t.palette.mode === 'dark' ? 0.12 : 0.06)} 100%)`,
        }}
      >
        <Stack spacing={1.5} sx={{ position: 'relative', zIndex: 1, maxWidth: 720 }}>
          <Typography component="h1" variant="h4" sx={{ fontWeight: 700, letterSpacing: '-0.02em' }}>
            How detection turns events into alerts
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.7 }}>
            The detection engine watches the agent event stream, remembers recent activity per device,
            and runs typed rules. When something looks like attack behavior or risky drift, it raises an
            alert you can open in TrustEdge. Click any step to see what happens there.
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ pt: 0.5 }}>
            <Button
              component={RouterLink}
              to="/alerts"
              variant="contained"
              size="small"
              endIcon={<ArrowForwardIcon />}
            >
              View alerts
            </Button>
            <Button component={RouterLink} to="/how-it-works" variant="outlined" size="small">
              Agent journey
            </Button>
          </Stack>
        </Stack>
        <Box className="agent-flow-hero-orb agent-flow-hero-orb--a" aria-hidden />
        <Box className="agent-flow-hero-orb agent-flow-hero-orb--b" aria-hidden />
      </Paper>

      <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1.5 }}>
        The detection path
      </Typography>

      <Box className="agent-flow-rail" sx={{ mb: 2.5 }}>
        {STEPS.map((step, index) => {
          const colors = toneColor(step.tone, theme);
          const selected = step.id === activeId;
          return (
            <Box key={step.id} className="agent-flow-rail-item">
              {index > 0 && (
                <Box
                  className="agent-flow-connector"
                  sx={{
                    background: (t) =>
                      `linear-gradient(90deg, ${alpha(t.palette.warning.main, 0.2)}, ${alpha(
                        t.palette.primary.main,
                        0.55,
                      )})`,
                  }}
                  aria-hidden
                />
              )}
              <button
                type="button"
                className={`agent-flow-step ${selected ? 'is-active' : ''}`}
                onClick={() => setActiveId(step.id)}
                aria-pressed={selected}
              >
                <Box
                  className="agent-flow-step-icon"
                  sx={{
                    bgcolor: colors.bg,
                    color: colors.fg,
                    boxShadow: selected ? `0 0 0 3px ${colors.ring}` : 'none',
                  }}
                >
                  {step.icon}
                </Box>
                <Typography
                  variant="caption"
                  sx={{
                    fontWeight: selected ? 700 : 500,
                    color: selected ? 'text.primary' : 'text.secondary',
                    textAlign: 'center',
                    lineHeight: 1.25,
                  }}
                >
                  {index + 1}. {step.title}
                </Typography>
              </button>
            </Box>
          );
        })}
      </Box>

      <Paper
        variant="outlined"
        className="agent-flow-detail"
        sx={{
          p: { xs: 2, md: 3 },
          mb: 3,
          borderColor: activeTone.ring,
          background: (t) =>
            `linear-gradient(180deg, ${alpha(activeTone.fg, t.palette.mode === 'dark' ? 0.08 : 0.04)} 0%, ${t.palette.background.paper} 48%)`,
        }}
      >
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'flex-start' }}>
          <Box
            sx={{
              width: 56,
              height: 56,
              borderRadius: 2,
              display: 'grid',
              placeItems: 'center',
              bgcolor: activeTone.bg,
              color: activeTone.fg,
              flexShrink: 0,
            }}
          >
            {active.icon}
          </Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="overline" color="text.secondary">
              Step {STEPS.findIndex((s) => s.id === active.id) + 1} of {STEPS.length}
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.75 }}>
              {active.title}
            </Typography>
            <Typography variant="body1" sx={{ mb: 1, lineHeight: 1.6 }}>
              {active.plain}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
              {active.detail}
            </Typography>
          </Box>
        </Stack>
      </Paper>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper variant="outlined" sx={{ p: 2.5, height: '100%' }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
              <CheckCircleOutlineIcon color="success" fontSize="small" />
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                What rules watch for
              </Typography>
            </Stack>
            <Stack spacing={1}>
              {COVERS.map((item) => (
                <Stack key={item} direction="row" spacing={1} alignItems="center">
                  <Box
                    sx={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      bgcolor: 'success.main',
                      flexShrink: 0,
                    }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    {item}
                  </Typography>
                </Stack>
              ))}
            </Stack>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper variant="outlined" sx={{ p: 2.5, height: '100%' }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
              <BlockOutlinedIcon color="action" fontSize="small" />
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                What this engine is not
              </Typography>
            </Stack>
            <Stack spacing={1}>
              {NOT_THIS.map((item) => (
                <Stack key={item} direction="row" spacing={1} alignItems="center">
                  <Box
                    sx={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      bgcolor: 'text.disabled',
                      flexShrink: 0,
                    }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    {item}
                  </Typography>
                </Stack>
              ))}
            </Stack>
          </Paper>
        </Grid>
      </Grid>

      <Paper
        variant="outlined"
        sx={{
          p: 2.5,
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          alignItems: { sm: 'center' },
          justifyContent: 'space-between',
          gap: 2,
        }}
      >
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            See detection in action
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Browse live alerts, or open an agent to see findings scoped to one device.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Button component={RouterLink} to="/alerts" variant="contained" size="small">
            Alerts
          </Button>
          <Button component={RouterLink} to="/agents" variant="outlined" size="small">
            Agents
          </Button>
          <Button component={RouterLink} to="/how-it-works" variant="text" size="small">
            Agent journey
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
}
