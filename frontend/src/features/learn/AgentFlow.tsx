import { useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import { alpha, useTheme } from '@mui/material/styles';
import LaptopMacIcon from '@mui/icons-material/LaptopMac';
import SensorsIcon from '@mui/icons-material/Sensors';
import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined';
import CompressIcon from '@mui/icons-material/Compress';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined';
import HubOutlinedIcon from '@mui/icons-material/HubOutlined';
import RuleOutlinedIcon from '@mui/icons-material/RuleOutlined';
import NotificationsActiveOutlinedIcon from '@mui/icons-material/NotificationsActiveOutlined';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import VisibilityOffOutlinedIcon from '@mui/icons-material/VisibilityOffOutlined';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
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
    id: 'endpoint',
    title: 'Endpoint',
    plain: 'A lightweight TrustEdge Agent runs on the laptop or workstation.',
    detail:
      'macOS, Linux, and Windows. No VPN required — the agent stays on-device, privacy-aware, and keeps collecting when the network is flaky.',
    icon: <LaptopMacIcon fontSize="small" />,
    tone: 'edge',
  },
  {
    id: 'collect',
    title: 'Collect',
    plain: 'Local collectors gather security-relevant posture — not a full dump of the machine.',
    detail:
      'Device details, activity, network summary and connection samples, process lifecycle, security persistence, and AI tools inventory.',
    icon: <SensorsIcon fontSize="small" />,
    tone: 'edge',
  },
  {
    id: 'queue',
    title: 'Durable queue',
    plain: 'Events land in an on-disk ring so telemetry survives offline and flaky links.',
    detail: 'Overwrite-oldest under pressure; flush by size or short timer. Delivery is reliable without blocking collection.',
    icon: <Inventory2OutlinedIcon fontSize="small" />,
    tone: 'path',
  },
  {
    id: 'compress',
    title: 'Compress',
    plain: 'Batches are compressed with zstd when it shrinks the payload.',
    detail: 'Less bandwidth on the way out — the security signal stays intact.',
    icon: <CompressIcon fontSize="small" />,
    tone: 'path',
  },
  {
    id: 'upload',
    title: 'Secure upload',
    plain: 'HTTPS upload to Agent API with the device’s own token.',
    detail: 'Credentials live in the OS keyring. Failed uploads retry with backoff; queued events remain until acknowledged.',
    icon: <LockOutlinedIcon fontSize="small" />,
    tone: 'path',
  },
  {
    id: 'ingest',
    title: 'Agent API',
    plain: 'Ingest authenticates the device, validates the batch, and refreshes the live twin.',
    detail: 'Accepted events are published onto the stream bus. The control plane can already show fresh agent posture.',
    icon: <CloudUploadOutlinedIcon fontSize="small" />,
    tone: 'cloud',
  },
  {
    id: 'stream',
    title: 'Kafka stream',
    plain: 'Validated events flow on a durable, ordered topic.',
    detail: 'Kafka / Redpanda carries trustedge.agent.events so detection can consume independently of ingest.',
    icon: <HubOutlinedIcon fontSize="small" />,
    tone: 'cloud',
  },
  {
    id: 'detect',
    title: 'Detect',
    plain: 'Multi-engine detection: YAML attack/chain rules, behavior baselines, and AI activity analysis.',
    detail:
      'Deterministic engines — not an LLM verdict. Hits fuse into scored findings for operators.',
    icon: <RuleOutlinedIcon fontSize="small" />,
    tone: 'detect',
  },
  {
    id: 'alert',
    title: 'Operate',
    plain: 'Attack alerts surface in the TrustEdge dashboard with evidence and agent context.',
    detail: 'Optional LLMs (Ollama / OpenAI / templates) explain what already fired — they never decide what is malicious.',
    icon: <NotificationsActiveOutlinedIcon fontSize="small" />,
    tone: 'detect',
  },
];

const COLLECTS = [
  'Device posture and agent health',
  'Process starts / exits and activity (focus & idle)',
  'Network summary and connection samples',
  'Security lifecycle (drivers, services, persistence)',
  'AI tools inventory (apps, CLI agents, runtimes, IDE extensions)',
];

const NEVER = [
  'Window titles or browsing URLs',
  'Keystrokes or clipboard',
  'Screenshots or file contents',
  'Raw Wi‑Fi SSIDs or full connection-table dumps',
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

export default function AgentFlow() {
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
            `linear-gradient(135deg, ${alpha(t.palette.primary.main, t.palette.mode === 'dark' ? 0.16 : 0.08)} 0%, ${alpha(
              t.palette.background.paper,
              0.4,
            )} 55%, ${alpha(t.palette.info.main, t.palette.mode === 'dark' ? 0.1 : 0.06)} 100%)`,
        }}
      >
        <Stack spacing={1.5} sx={{ position: 'relative', zIndex: 1, maxWidth: 720 }}>
          <Typography component="h1" variant="h4" sx={{ fontWeight: 700, letterSpacing: '-0.02em' }}>
            How it works
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.7 }}>
            Collect on the endpoint, deliver over HTTPS, stream on Kafka, then detect and operate.
            TrustEdge Agent gathers security-relevant posture into a durable queue, uploads to Agent API,
            and multi-engine detection raises attack alerts in the dashboard. Select a step for detail.
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ pt: 0.5 }}>
            <Button
              component={RouterLink}
              to="/agents"
              variant="contained"
              size="small"
              endIcon={<ArrowForwardIcon />}
            >
              View agents
            </Button>
            <Button component={RouterLink} to="/how-detection-works" variant="outlined" size="small">
              Detection engine
            </Button>
          </Stack>
        </Stack>
        <Box className="agent-flow-hero-orb agent-flow-hero-orb--a" aria-hidden />
        <Box className="agent-flow-hero-orb agent-flow-hero-orb--b" aria-hidden />
      </Paper>

      <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1.5 }}>
        Pipeline — Edge · Ingest · Stream · Detect · Operate
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
                      `linear-gradient(90deg, ${alpha(t.palette.primary.main, 0.15)}, ${alpha(
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
                Endpoint telemetry
              </Typography>
            </Stack>
            <Stack spacing={1}>
              {COLLECTS.map((item) => (
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
              <VisibilityOffOutlinedIcon color="action" fontSize="small" />
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                Privacy boundaries
              </Typography>
            </Stack>
            <Stack spacing={1}>
              {NEVER.map((item) => (
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
            See it on a live agent
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Open Agents for twin state, AI tools inventory, and timeline — or Alerts for findings with evidence.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Button component={RouterLink} to="/agents" variant="contained" size="small">
            Agents
          </Button>
          <Button component={RouterLink} to="/alerts" variant="outlined" size="small">
            Alerts
          </Button>
          <Button component={RouterLink} to="/how-detection-works" variant="text" size="small">
            Detection engine
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
}
