import { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import Link from '@mui/material/Link';
import DashboardCard from './DashboardCard';
import { twinApi } from '../../../twin/config/api';
import { ConnectedAgent } from '../../../twin/types/connectedAgent';

function formatAgentLabel(agent: ConnectedAgent): string {
  return agent.hostname || agent.device_id;
}

export default function AgentStatusCard() {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<ConnectedAgent[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await twinApi.listConnectedAgents(300);
        if (!cancelled) setItems(result.items || []);
      } catch {
        if (!cancelled) setItems([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const ranked = [...items]
    .sort((a, b) => Number(b.connected) - Number(a.connected))
    .slice(0, 5);

  return (
    <DashboardCard
      title="Agent status"
      action={
        <Link component={RouterLink} to="/agents" variant="caption" underline="hover" color="text.secondary">
          Show all
        </Link>
      }
    >
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress size={24} />
        </Box>
      ) : ranked.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
          No agents reporting yet.
        </Typography>
      ) : (
        <Table size="small" sx={{ '& td, & th': { borderColor: 'divider', px: 0.5 } }}>
          <TableHead>
            <TableRow>
              {['#', 'Agent', 'Status', 'Network', 'Conns'].map((h) => (
                <TableCell
                  key={h}
                  sx={{
                    color: 'text.secondary',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    py: 1,
                  }}
                >
                  {h}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {ranked.map((agent, idx) => (
              <TableRow
                key={agent.device_id}
                hover
                component={RouterLink}
                to={`/agents/${encodeURIComponent(agent.device_id)}`}
                sx={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
              >
                <TableCell sx={{ py: 1.25, color: 'text.secondary', width: 28 }}>{idx + 1}</TableCell>
                <TableCell sx={{ py: 1.25 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }} noWrap>
                    {formatAgentLabel(agent)}
                  </Typography>
                </TableCell>
                <TableCell sx={{ py: 1.25 }}>
                  <Stack direction="row" spacing={0.75} alignItems="center">
                    <Box
                      sx={{
                        width: 7,
                        height: 7,
                        borderRadius: '50%',
                        bgcolor: agent.connected ? 'success.main' : 'grey.400',
                      }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {agent.connected ? 'Live' : 'Idle'}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell sx={{ py: 1.25 }}>
                  <Typography variant="caption" color="text.secondary">
                    {agent.network_type || '—'}
                  </Typography>
                </TableCell>
                <TableCell sx={{ py: 1.25 }}>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {agent.established_count ?? '—'}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </DashboardCard>
  );
}
