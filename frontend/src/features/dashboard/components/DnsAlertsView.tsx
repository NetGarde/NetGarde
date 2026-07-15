import { useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import RefreshIcon from '@mui/icons-material/Refresh';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import SearchIcon from '@mui/icons-material/Search';
import { useDnsAlerts } from '../../dns-queries/hooks/useDnsAlerts';
import { useDomainWhois } from '../../dns-queries/hooks/useDomainWhois';
import { DnsAlert } from '../../dns-queries/types/dnsQuery';
import { formatShortDateTime } from '../../../shared/utils/dateUtils';

const SEVERITY_COLOR: Record<string, 'error' | 'warning' | 'info' | 'default'> = {
  high: 'error',
  medium: 'warning',
  low: 'info',
};

const TYPE_LABEL: Record<string, string> = {
  blocked_attempt: 'Blocked',
  new_domain: 'New site',
  suspicious_domain: 'Suspicious',
  bandwidth_spike: 'Bandwidth',
  behavior_anomaly: 'Behavior',
  new_country_region: 'New region',
  forbidden_country_access: 'Forbidden country',
};

function lookupDomainForAlert(alert: DnsAlert): string | null {
  return alert.root_domain || alert.domain;
}

function splitAlertReasons(message: string | null): string[] {
  if (!message?.trim()) return [];
  return message
    .split(';')
    .map((part) => part.trim())
    .filter(Boolean);
}

function DetailRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <Stack direction="row" spacing={2} sx={{ py: 0.5 }}>
      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 110, flexShrink: 0 }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>
        {value}
      </Typography>
    </Stack>
  );
}

function AlertDetailsTab({ alert }: { alert: DnsAlert }) {
  const label = TYPE_LABEL[alert.alert_type] || alert.alert_type;
  const severity = SEVERITY_COLOR[alert.severity] || 'default';
  const reasons = splitAlertReasons(alert.message);
  const whyLabel =
    alert.alert_type === 'suspicious_domain'
      ? 'Why suspicious'
      : alert.alert_type === 'blocked_attempt'
        ? 'Block reason'
        : alert.alert_type === 'new_domain'
          ? 'Details'
          : 'Details';

  return (
    <Stack spacing={2} sx={{ pt: 1 }}>
      <Stack direction="row" spacing={1} flexWrap="wrap">
        <Chip label={label} size="small" color={severity} variant="outlined" />
        <Chip label={`Severity: ${alert.severity}`} size="small" variant="outlined" />
      </Stack>

      <Box>
        <DetailRow label="Domain" value={alert.domain} />
        <DetailRow label="Root domain" value={alert.root_domain} />
        <DetailRow label="Client IP" value={alert.client_ip} />
        <DetailRow label="Detected" value={formatShortDateTime(alert.timestamp)} />
      </Box>

      {reasons.length > 0 && (
        <Box>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {whyLabel}
          </Typography>
          <Stack spacing={1}>
            {reasons.map((reason, index) => (
              <Alert
                key={`${index}-${reason}`}
                severity={alert.alert_type === 'suspicious_domain' ? 'warning' : 'info'}
                sx={{ py: 0.5 }}
              >
                {reason}
              </Alert>
            ))}
          </Stack>
        </Box>
      )}

      {reasons.length === 0 && alert.message && (
        <Alert severity="info">{alert.message}</Alert>
      )}
    </Stack>
  );
}

function WhoisTab({
  loading,
  error,
  result,
}: {
  loading: boolean;
  error: string | null;
  result: { domain: string; source: string; text: string } | null;
}) {
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress size={28} />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!result) {
    return (
      <Typography color="text.secondary" sx={{ py: 2 }}>
        No WHOIS data loaded yet.
      </Typography>
    );
  }

  return (
    <Stack spacing={1} sx={{ pt: 1 }}>
      <Chip label={`Source: ${result.source}`} size="small" variant="outlined" sx={{ alignSelf: 'flex-start' }} />
      <Box
        component="pre"
        sx={{
          m: 0,
          p: 1.5,
          bgcolor: 'action.hover',
          borderRadius: 1,
          overflow: 'auto',
          maxHeight: 420,
          fontFamily: 'monospace',
          fontSize: '0.8rem',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {result.text}
      </Box>
    </Stack>
  );
}

function AlertRow({
  alert,
  onInspect,
}: {
  alert: DnsAlert;
  onInspect: (alert: DnsAlert) => void;
}) {
  const label = TYPE_LABEL[alert.alert_type] || alert.alert_type;
  const severity = SEVERITY_COLOR[alert.severity] || 'default';
  const inspectDomain = lookupDomainForAlert(alert);

  return (
    <ListItem
      sx={{ py: 0.75, px: 1.5 }}
      secondaryAction={
        inspectDomain ? (
          <Tooltip title={`Details & WHOIS: ${inspectDomain}`}>
            <IconButton edge="end" size="small" aria-label="View details and WHOIS" onClick={() => onInspect(alert)}>
              <SearchIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        ) : undefined
      }
    >
      <ListItemText
        primary={
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" sx={{ pr: inspectDomain ? 4 : 0 }}>
            <Chip label={label} size="small" color={severity} variant="outlined" />
            <Typography variant="body2" sx={{ fontWeight: 600, flex: 1 }}>
              {alert.domain || alert.root_domain || alert.message || 'Alert'}
            </Typography>
          </Stack>
        }
        secondary={
          <Stack spacing={0.75} sx={{ mt: 0.5 }}>
            <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap">
              <Typography variant="caption" color="text.secondary">
                {formatShortDateTime(alert.timestamp)}
              </Typography>
              {alert.client_ip && (
                <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                  {alert.client_ip}
                </Typography>
              )}
            </Stack>
            {alert.message && alert.alert_type !== 'suspicious_domain' && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                {alert.message}
              </Typography>
            )}
          </Stack>
        }
      />
    </ListItem>
  );
}

export default function DnsAlertsView() {
  const { items, total, loading, refetch } = useDnsAlerts();
  const { lookup, loading: whoisLoading, error: whoisError, result: whoisResult, reset: resetWhois } =
    useDomainWhois();
  const [inspectOpen, setInspectOpen] = useState(false);
  const [inspectAlert, setInspectAlert] = useState<DnsAlert | null>(null);
  const [dialogTab, setDialogTab] = useState(0);

  const handleInspect = async (alert: DnsAlert) => {
    const domain = lookupDomainForAlert(alert);
    if (!domain) return;
    setInspectAlert(alert);
    setDialogTab(0);
    setInspectOpen(true);
    resetWhois();
    await lookup(domain);
  };

  const handleCloseInspect = () => {
    setInspectOpen(false);
    setInspectAlert(null);
    setDialogTab(0);
    resetWhois();
  };

  const handleRefreshWhois = async () => {
    if (!inspectAlert) return;
    const domain = lookupDomainForAlert(inspectAlert);
    if (!domain) return;
    await lookup(domain);
  };

  const inspectDomain = inspectAlert ? lookupDomainForAlert(inspectAlert) : null;

  return (
    <>
      <Paper
        variant="outlined"
        sx={{
          height: '100%',
          minHeight: 280,
          maxHeight: 420,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ px: 2, py: 1.5 }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <WarningAmberIcon color="warning" fontSize="small" />
            <Typography variant="subtitle2">Anomaly Alerts</Typography>
            {total > 0 && <Chip label={total} size="small" color="warning" variant="outlined" />}
          </Stack>
          <Tooltip title="Refresh">
            <IconButton size="small" onClick={refetch} disabled={loading}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
        <Divider />
        <Box sx={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden' }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress size={28} />
            </Box>
          ) : items.length === 0 ? (
            <Typography color="text.secondary" sx={{ p: 2 }}>
              No alerts yet. New domains, suspicious DNS, and behavior anomalies appear here.
            </Typography>
          ) : (
            <List dense disablePadding>
              {items.map((alert, index) => (
                <Box key={alert.id}>
                  <AlertRow alert={alert} onInspect={handleInspect} />
                  {index < items.length - 1 && <Divider component="li" />}
                </Box>
              ))}
            </List>
          )}
        </Box>
      </Paper>

      <Dialog open={inspectOpen} onClose={handleCloseInspect} maxWidth="md" fullWidth>
        <DialogTitle>
          Domain investigation
          {inspectDomain ? ` — ${inspectDomain}` : ''}
        </DialogTitle>
        <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
          <Tabs value={dialogTab} onChange={(_, value) => setDialogTab(value)} aria-label="Alert investigation tabs">
            <Tab label="Alert details" />
            <Tab label="WHOIS" />
          </Tabs>
        </Box>
        <DialogContent dividers sx={{ minHeight: 280 }}>
          {inspectAlert && dialogTab === 0 && <AlertDetailsTab alert={inspectAlert} />}
          {dialogTab === 1 && (
            <WhoisTab loading={whoisLoading} error={whoisError} result={whoisResult} />
          )}
        </DialogContent>
        <DialogActions>
          {dialogTab === 1 && inspectDomain && (
            <Button onClick={handleRefreshWhois} disabled={whoisLoading}>
              Refresh WHOIS
            </Button>
          )}
          <Button onClick={handleCloseInspect}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
