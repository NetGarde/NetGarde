import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import RefreshIcon from '@mui/icons-material/Refresh';
import AutoAwesomeOutlinedIcon from '@mui/icons-material/AutoAwesomeOutlined';
import { useNetworkOverview } from '../../hooks/useNetworkOverview';
import { formatShortDateTime } from '../../../../shared/utils/dateUtils';

export default function AiOverviewCard() {
  const { data, loading, error, refetch } = useNetworkOverview(60);

  const stats = data?.stats;
  const isAi = data?.source === 'llm';
  const reviewText =
    data?.summary?.trim() ||
    (isAi && (data?.bullets?.length ?? 0) > 0 ? data!.bullets.join(' ') : '');
  const wantsAi = data?.review_mode === 'ollama' || data?.review_mode === 'openai';
  const showFallbackHint = wantsAi && !isAi && !loading;

  return (
    <Paper variant="outlined" sx={{ p: 2.5 }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }}>
        <AutoAwesomeOutlinedIcon color="primary" fontSize="small" />
        <Typography component="h3" variant="subtitle2" sx={{ fontWeight: 600, flex: 1 }}>
          AI overview
        </Typography>
        {data && (
          <Stack direction="row" spacing={0.75} alignItems="center">
            {isAi && data.llm_model && (
              <Chip size="small" label={data.llm_model} variant="outlined" color="primary" />
            )}
            {!isAi && <Chip size="small" label="Rules-based fallback" variant="outlined" color="warning" />}
            <Typography variant="caption" color="text.secondary">
              Last {data.period_minutes} min · {formatShortDateTime(data.generated_at)}
            </Typography>
          </Stack>
        )}
        <Tooltip title="Regenerate AI overview">
          <span>
            <IconButton
              size="small"
              onClick={() => refetch(true)}
              disabled={loading}
              aria-label="Regenerate AI overview"
            >
              {loading ? <CircularProgress size={18} /> : <RefreshIcon fontSize="small" />}
            </IconButton>
          </span>
        </Tooltip>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 1.5 }}>
          {error}
        </Alert>
      )}

      {showFallbackHint && (
        <Alert severity="warning" sx={{ mb: 1.5 }}>
          {data?.llm_error ? (
            <>
              <strong>AI error:</strong> {data.llm_error}
            </>
          ) : (
            <>
              AI is configured ({data?.review_mode}) but the API returned a rules-based summary. Run on EC2:{' '}
              <code>sudo bash ~/trustedge/scripts/ec2-setup-ollama.sh</code>
            </>
          )}
        </Alert>
      )}

      {loading && !data && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Generating AI overview… On CPU this can take up to 2 minutes the first time.
        </Typography>
      )}

      {stats && !isAi && (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
          <Chip size="small" label={`${stats.reporting_clients} live`} variant="outlined" />
          <Chip size="small" label={`${stats.live_total_mib_per_sec.toFixed(1)} MiB/s now`} variant="outlined" />
          <Chip size="small" label={`Peak ${stats.peak_mib_per_sec.toFixed(1)} MiB/s`} variant="outlined" />
          <Chip
            size="small"
            label={`${stats.alerts_total} alerts`}
            color={stats.alerts_total > 0 ? 'warning' : 'default'}
            variant="outlined"
          />
        </Stack>
      )}

      {loading && !data ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
          <CircularProgress size={28} />
        </Box>
      ) : reviewText ? (
        <Typography variant="body2" color="text.primary" sx={{ lineHeight: 1.65 }}>
          {reviewText}
        </Typography>
      ) : (
        <List dense disablePadding>
          {(data?.bullets ?? []).map((bullet, index) => (
            <ListItem key={index} disableGutters sx={{ py: 0.25 }}>
              <ListItemIcon sx={{ minWidth: 28 }}>
                <FiberManualRecordIcon sx={{ fontSize: 8, color: 'text.secondary' }} />
              </ListItemIcon>
              <ListItemText
                primary={bullet}
                primaryTypographyProps={{ variant: 'body2', color: 'text.primary' }}
              />
            </ListItem>
          ))}
        </List>
      )}
    </Paper>
  );
}
