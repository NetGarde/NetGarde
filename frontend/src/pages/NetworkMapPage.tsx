import { lazy, Suspense } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Chip from '@mui/material/Chip';
import { Link as RouterLink } from 'react-router-dom';
import TableChartIcon from '@mui/icons-material/TableChart';

const NetworkAttributionMapGraph = lazy(
  () => import('../features/network-map/components/NetworkAttributionMapGraph'),
);

export default function NetworkMapPage() {
  return (
    <Box sx={{ maxWidth: 1200 }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'flex-start' }}
        spacing={1}
        sx={{ mb: 2 }}
      >
        <Box>
          <Typography component="h1" variant="h5" sx={{ mb: 0.5, fontWeight: 600 }}>
            Network map
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Who talked to what: destinations table first, path diagram for one client.
          </Typography>
        </Box>
        <Stack direction="row" flexWrap="wrap" gap={0.75} sx={{ flexShrink: 0 }}>
          <Chip size="small" variant="outlined" icon={<TableChartIcon />} label="Destinations + path" />
        </Stack>
      </Stack>

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Scan the destinations table for who talked to what. The path diagram stays minimal (egress summary)
          until you click a row to inspect one destination. Blocked DNS is red. Filter by client or VPN vs
          agents as needed.
        </Typography>
        <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mt: 1.5 }}>
          <Button component={RouterLink} to="/client-map" size="small" variant="outlined">
            Geographic client map
          </Button>
          <Button component={RouterLink} to="/client-profiles" size="small" variant="text">
            Client profiles
          </Button>
        </Stack>
      </Paper>

      <Suspense
        fallback={
          <Paper variant="outlined" sx={{ p: 6, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress size={32} />
          </Paper>
        }
      >
        <NetworkAttributionMapGraph showHeader={false} />
      </Suspense>
    </Box>
  );
}
