import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import { Link as RouterLink } from 'react-router-dom';
import { useAgents } from './hooks/useAgents';
import { isAgentOnline } from './utils/presence';
import { formatShortDateTime } from '../../shared/utils/dateUtils';

export default function AgentsList() {
  const { agents, loading, error, refresh } = useAgents();

  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2.5 }}>
        <Box>
          <Typography
            component="h1"
            sx={{
              fontWeight: 700,
              fontSize: { xs: '1.5rem', md: '1.75rem' },
              letterSpacing: '-0.03em',
              color: 'text.primary',
              lineHeight: 1.2,
              mb: 0.75,
            }}
          >
            Agents
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Registered TrustEdge Agent installs. Online means last seen within the last 5 minutes.
          </Typography>
        </Box>
        <Button
          size="small"
          variant="outlined"
          onClick={refresh}
          disabled={loading}
          sx={{
            borderColor: 'divider',
            color: 'text.primary',
            bgcolor: 'background.paper',
            textTransform: 'none',
            fontWeight: 500,
            borderRadius: '8px',
            '&:hover': { borderColor: 'grey.400', bgcolor: 'grey.50' },
          }}
        >
          Refresh
        </Button>
      </Stack>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!loading && agents.length === 0 && !error && (
        <Alert severity="info" variant="outlined">
          No agents registered yet. Stations appear after the TrustEdge Agent enrolls via Agent-API.
        </Alert>
      )}

      {!loading && agents.length > 0 && (
        <Paper variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Hostname</TableCell>
                <TableCell>Agent ID</TableCell>
                <TableCell>OS</TableCell>
                <TableCell>Version</TableCell>
                <TableCell>Presence</TableCell>
                <TableCell>Installed</TableCell>
                <TableCell>Last seen</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {agents.map((agent) => {
                const online = isAgentOnline(agent.last_seen_at);
                return (
                  <TableRow
                    key={agent.agent_id}
                    hover
                    component={RouterLink}
                    to={`/agents/${encodeURIComponent(agent.agent_id)}`}
                    sx={{
                      textDecoration: 'none',
                      color: 'inherit',
                      cursor: 'pointer',
                    }}
                  >
                    <TableCell>{agent.hostname || '—'}</TableCell>
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                      {agent.agent_id}
                    </TableCell>
                    <TableCell>
                      {[agent.os, agent.os_version, agent.arch].filter(Boolean).join(' · ') || '—'}
                    </TableCell>
                    <TableCell>{agent.agent_version || '—'}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={online ? 'online' : 'offline'}
                        color={online ? 'success' : 'default'}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>{formatShortDateTime(agent.first_seen_at)}</TableCell>
                    <TableCell>{formatShortDateTime(agent.last_seen_at)}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Box>
  );
}
