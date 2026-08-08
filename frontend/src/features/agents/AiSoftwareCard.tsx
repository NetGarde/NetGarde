import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Tooltip from '@mui/material/Tooltip';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import type { AiSoftwareItem } from '../twin/types/aiSoftware';
import { aiAppIcon, isCliAgent } from './utils/aiAppIcons';
import { confidenceChipColor, explainConfidence } from './utils/aiConfidenceDisplay';

type Props = {
  items: AiSoftwareItem[];
  loading: boolean;
  error: string | null;
};

const CATEGORY_LABELS: Record<string, string> = {
  code_editor: 'Code editor',
  chat_client: 'Chat client',
  cli_agent: 'CLI agent',
};

function categoryLabel(category: string): string {
  if (!category) return '—';
  const key = category.trim().toLowerCase();
  return CATEGORY_LABELS[key] || category.replace(/_/g, ' ');
}

function BoolChip({ value, yesLabel, noLabel }: { value: boolean; yesLabel: string; noLabel: string }) {
  return (
    <Chip
      size="small"
      label={value ? yesLabel : noLabel}
      color={value ? 'success' : 'default'}
      variant={value ? 'filled' : 'outlined'}
      sx={{ height: 22, fontSize: '0.75rem' }}
    />
  );
}

function ConfidenceCell({ item }: { item: AiSoftwareItem }) {
  if (!item.confidence) {
    return (
      <Typography variant="body2" color="text.secondary">
        —
      </Typography>
    );
  }

  const expl = explainConfidence(item);
  const title = (
    <Box sx={{ maxWidth: 360, py: 0.5 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
        {expl.level}
      </Typography>
      <Typography variant="body2" sx={{ mb: expl.matched.length || expl.failed.length ? 1 : 0, lineHeight: 1.4 }}>
        {expl.summary}
      </Typography>
      {!expl.fromAgent && expl.matched.length > 0 ? (
        <Typography variant="caption" component="div" sx={{ display: 'block', mb: 0.5 }}>
          Matched: {expl.matched.join(', ')}
        </Typography>
      ) : null}
      {!expl.fromAgent && expl.failed.length > 0 ? (
        <Typography variant="caption" component="div" sx={{ display: 'block' }}>
          Missing: {expl.failed.join(', ')}
        </Typography>
      ) : null}
    </Box>
  );

  return (
    <Stack spacing={0.5} sx={{ maxWidth: 360 }}>
      <Tooltip title={title} arrow placement="top" enterTouchDelay={0}>
        <Chip
          size="small"
          icon={<InfoOutlinedIcon sx={{ fontSize: '14px !important' }} />}
          label={expl.level}
          color={confidenceChipColor(expl.level)}
          variant="outlined"
          sx={{ height: 22, fontSize: '0.75rem', fontFamily: 'monospace', cursor: 'help', alignSelf: 'flex-start' }}
        />
      </Tooltip>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ lineHeight: 1.35, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
      >
        {expl.summary}
      </Typography>
    </Stack>
  );
}

function PathCell({ item }: { item: AiSoftwareItem }) {
  const cli = isCliAgent(item.product_id, item.category);
  const displayPath = (cli && item.invocation_path) || item.path || item.resolved_path || '—';
  const packageBits = [item.package_manager, item.package_identifier].filter(Boolean).join(' · ');

  return (
    <Stack spacing={0.25} sx={{ maxWidth: 320 }}>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}
      >
        {displayPath}
      </Typography>
      {packageBits ? (
        <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
          {packageBits}
        </Typography>
      ) : null}
    </Stack>
  );
}

export default function AiSoftwareCard({ items, loading, error }: Props) {
  if (loading && items.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
        <CircularProgress size={28} />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" variant="outlined">
        {error}
      </Alert>
    );
  }

  if (!items.length) {
    return (
      <Alert severity="info" variant="outlined">
        No installed AI apps or CLI agents reported for this agent yet.
      </Alert>
    );
  }

  return (
    <Box sx={{ overflowX: 'auto' }}>
      <Table size="small" aria-label="Installed AI software">
        <TableHead>
          <TableRow>
            <TableCell>Product</TableCell>
            <TableCell>Vendor</TableCell>
            <TableCell>Version</TableCell>
            <TableCell>Category</TableCell>
            <TableCell>Running</TableCell>
            <TableCell>Confidence</TableCell>
            <TableCell>Path</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {items.map((item) => {
            const cli = isCliAgent(item.product_id, item.category);
            return (
              <TableRow key={item.id} hover>
                <TableCell>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Box
                      sx={{
                        display: 'inline-flex',
                        color: 'text.primary',
                        flexShrink: 0,
                        '& > svg': { fontSize: 18 },
                      }}
                      aria-hidden
                    >
                      {aiAppIcon(item.product_id, undefined, item.category)}
                    </Box>
                    <Stack spacing={0.25}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {item.product_name || item.product_id || item.id}
                      </Typography>
                      {cli && item.executable ? (
                        <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                          {item.executable}
                        </Typography>
                      ) : null}
                    </Stack>
                  </Stack>
                </TableCell>
                <TableCell>{item.vendor || '—'}</TableCell>
                <TableCell>{item.version || '—'}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={categoryLabel(item.category)}
                    variant="outlined"
                    sx={{ height: 22, fontSize: '0.75rem', textTransform: 'none' }}
                  />
                </TableCell>
                <TableCell>
                  <BoolChip value={item.running} yesLabel="Running" noLabel="Idle" />
                </TableCell>
                <TableCell>
                  <ConfidenceCell item={item} />
                </TableCell>
                <TableCell>
                  <PathCell item={item} />
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Box>
  );
}
