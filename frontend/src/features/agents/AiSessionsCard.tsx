import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import type {
  AiActivityChainStep,
  AiSessionChainResponse,
  AiSessionGraphResponse,
  AiSessionSummary,
  AiSessionTimelineResponse,
} from '../twin/types/aiActivity';
import {
  appDisplayName,
  formatDurationMs,
  riskTone,
  sessionSubtitle,
} from './utils/aiSessionDisplay';
import { formatShortDateTime } from '../../shared/utils/dateUtils';

type Props = {
  items: AiSessionSummary[];
  loading: boolean;
  error: string | null;
  selectedId: string | null;
  onSelect: (sessionId: string | null) => void;
  detailLoading: boolean;
  chain: AiSessionChainResponse | null;
  graph: AiSessionGraphResponse | null;
  timeline: AiSessionTimelineResponse | null;
};

function stepAccent(kind: string): string {
  switch (kind) {
    case 'app':
      return 'primary.main';
    case 'secret':
      return 'error.main';
    case 'network':
    case 'cloud':
      return 'warning.main';
    case 'tool':
      return 'info.main';
    case 'files':
      return 'success.main';
    default:
      return 'text.secondary';
  }
}

function ActivityChain({ steps }: { steps: AiActivityChainStep[] }) {
  if (!steps.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No activity steps reconstructed for this session yet.
      </Typography>
    );
  }

  return (
    <Stack spacing={0} sx={{ mt: 0.5 }}>
      {steps.map((step, idx) => (
        <Box key={`${step.kind}-${step.label}-${idx}`}>
          {idx > 0 ? (
            <Typography
              variant="body2"
              color="text.disabled"
              sx={{ pl: 0.75, lineHeight: 1.2, userSelect: 'none' }}
              aria-hidden
            >
              ↓
            </Typography>
          ) : null}
          <Stack direction="row" spacing={1} alignItems="baseline">
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                bgcolor: stepAccent(step.kind),
                flexShrink: 0,
                mt: '6px',
              }}
            />
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {step.label}
              </Typography>
              {step.detail ? (
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: 'block', fontFamily: 'monospace', wordBreak: 'break-all' }}
                >
                  {step.detail}
                </Typography>
              ) : null}
            </Box>
          </Stack>
        </Box>
      ))}
    </Stack>
  );
}

export default function AiSessionsCard({
  items,
  loading,
  error,
  selectedId,
  onSelect,
  detailLoading,
  chain,
  graph,
  timeline,
}: Props) {
  if (loading && items.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
        <CircularProgress size={28} />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="warning" sx={{ mb: 1 }}>
        {error}
      </Alert>
    );
  }

  if (!items.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No AI application sessions reconstructed yet. Activity from Cursor, Claude, VS Code, and
        similar tools will appear here.
      </Typography>
    );
  }

  const selected = items.find((s) => s.session_id === selectedId) || null;

  return (
    <Stack spacing={2}>
      <List dense disablePadding>
        {items.map((session) => (
          <ListItemButton
            key={session.session_id}
            selected={session.session_id === selectedId}
            onClick={() =>
              onSelect(session.session_id === selectedId ? null : session.session_id)
            }
            sx={{ borderRadius: 1, mb: 0.5 }}
          >
            <ListItemText
              primary={
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {appDisplayName(session.app_name)}
                  </Typography>
                  <Chip
                    label={session.status}
                    size="small"
                    variant="outlined"
                    color={session.status === 'active' ? 'success' : 'default'}
                  />
                  <Chip
                    label={`risk ${session.risk_score}`}
                    size="small"
                    color={riskTone(session.risk_score)}
                  />
                </Stack>
              }
              secondary={`${formatShortDateTime(session.start_time)} · ${formatDurationMs(session.duration_ms)} · ${sessionSubtitle(session)}`}
            />
          </ListItemButton>
        ))}
      </List>

      {selected ? (
        <>
          <Divider />
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Activity chain
          </Typography>

          {detailLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
              <CircularProgress size={24} />
            </Box>
          ) : (
            <Stack spacing={2}>
              <ActivityChain steps={chain?.items || []} />

              {graph?.graph?.nodes?.length ? (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                    Process tree
                  </Typography>
                  <Stack spacing={0.5} sx={{ mt: 0.5 }}>
                    {graph.graph.nodes.slice(0, 24).map((node, idx) => (
                      <Typography key={node.id} variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {idx === 0 ? '●' : '↓'} {node.label}
                        {node.role ? ` (${node.role})` : ''}
                      </Typography>
                    ))}
                  </Stack>
                </Box>
              ) : null}

              {timeline?.items?.length ? (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                    Timeline
                  </Typography>
                  <Stack spacing={0.75} sx={{ mt: 0.5 }}>
                    {timeline.items
                      .slice(-20)
                      .reverse()
                      .map((ev, i) => (
                        <Stack key={`${ev.timestamp}-${i}`} spacing={0}>
                          <Typography variant="caption" color="text.secondary">
                            {formatShortDateTime(ev.timestamp)} · {ev.kind}
                          </Typography>
                          <Typography variant="body2">{ev.summary}</Typography>
                        </Stack>
                      ))}
                  </Stack>
                </Box>
              ) : null}
            </Stack>
          )}
        </>
      ) : null}
    </Stack>
  );
}
