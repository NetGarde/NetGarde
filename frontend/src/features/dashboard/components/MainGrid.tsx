import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import Grid from '@mui/material/Grid';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import FileDownloadOutlinedIcon from '@mui/icons-material/FileDownloadOutlined';
import Copyright from '../internals/components/Copyright';
import HealthScoreCard from './widgets/HealthScoreCard';
import OverviewTrendCard from './widgets/OverviewTrendCard';
import AgentStatusCard from './widgets/AgentStatusCard';
import RecentAlertsCard from './widgets/RecentAlertsCard';
import TopAgentsCard from './widgets/TopAgentsCard';
import SeverityDonutCard from './widgets/SeverityDonutCard';
import AiOverviewCard from './widgets/AiOverviewCard';

export default function MainGrid() {
  return (
    <Box sx={{ width: '100%' }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'flex-start', sm: 'flex-start' }}
        spacing={2}
        sx={{ mb: 2.5 }}
      >
        <Box>
          <Typography
            component="h1"
            sx={{
              fontWeight: 700,
              fontSize: { xs: '1.5rem', md: '1.75rem' },
              letterSpacing: '-0.03em',
              color: 'text.primary',
              lineHeight: 1.2,
            }}
          >
            Overview
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
            Network health, agents, and detection signals at a glance.
          </Typography>
        </Box>
        <Button
          variant="outlined"
          size="small"
          startIcon={<FileDownloadOutlinedIcon />}
          sx={{
            borderColor: 'divider',
            color: 'text.primary',
            bgcolor: 'background.paper',
            textTransform: 'none',
            fontWeight: 500,
            borderRadius: '8px',
            px: 1.5,
            '&:hover': { borderColor: 'grey.400', bgcolor: 'grey.50' },
          }}
        >
          Export
        </Button>
      </Stack>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2.5 }}>
        {['Last 60 min', 'All agents', 'All severities', 'All types'].map((label) => (
          <FormControl key={label} size="small">
            <Select
              value={label}
              displayEmpty
              sx={{
                bgcolor: 'background.paper',
                borderRadius: '8px',
                fontSize: '0.8125rem',
                fontWeight: 500,
                color: 'text.primary',
                minWidth: 130,
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'divider' },
                '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'grey.400' },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: 'primary.main' },
              }}
            >
              <MenuItem value={label}>{label}</MenuItem>
            </Select>
          </FormControl>
        ))}
      </Stack>

      <Grid container spacing={2} columns={12} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, md: 3 }}>
          <HealthScoreCard />
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <OverviewTrendCard />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <AgentStatusCard />
        </Grid>
      </Grid>

      <Grid container spacing={2} columns={12} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <RecentAlertsCard />
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <TopAgentsCard />
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <SeverityDonutCard />
        </Grid>
      </Grid>

      <AiOverviewCard />

      <Copyright sx={{ my: 4 }} />
    </Box>
  );
}
