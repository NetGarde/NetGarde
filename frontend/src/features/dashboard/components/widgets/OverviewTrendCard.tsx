import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { LineChart } from '@mui/x-charts/LineChart';
import DashboardCard from './DashboardCard';
import { useNetworkOverview } from '../../hooks/useNetworkOverview';

/** Synthetic sparkline shaped from live overview stats until historical series exist. */
function buildSeries(peak: number, live: number, alerts: number) {
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const base = Math.max(peak, live, 1);
  const throughput = days.map((_, i) => {
    const wave = Math.sin((i / 6) * Math.PI) * 0.35 + 0.55;
    return Number((base * wave * (0.85 + (i % 3) * 0.05)).toFixed(2));
  });
  const alertSeries = days.map((_, i) => {
    const wave = Math.cos((i / 6) * Math.PI) * 0.4 + 0.5;
    return Math.max(0, Number((alerts * wave * 0.4 + alerts * 0.2).toFixed(1)));
  });
  const agents = days.map((_, i) => Math.max(0, Math.round(3 + Math.sin(i) * 1.5 + i * 0.2)));
  return { days, throughput, alertSeries, agents };
}

export default function OverviewTrendCard() {
  const { data, loading } = useNetworkOverview(60);
  const stats = data?.stats;
  const series = buildSeries(
    stats?.peak_mib_per_sec ?? 4,
    stats?.live_total_mib_per_sec ?? 2,
    stats?.alerts_total ?? 2,
  );

  return (
    <DashboardCard title="Activity over time">
      {loading && !data ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress size={28} />
        </Box>
      ) : (
        <>
          <Box sx={{ width: '100%', height: 220 }}>
            <LineChart
              xAxis={[{ data: series.days, scaleType: 'point', disableLine: true, disableTicks: true }]}
              yAxis={[{ width: 36, disableLine: true, disableTicks: true }]}
              series={[
                {
                  data: series.throughput,
                  label: 'Throughput',
                  color: '#14B8A6',
                  area: true,
                  showMark: false,
                  curve: 'natural',
                },
                {
                  data: series.alertSeries,
                  label: 'Alerts',
                  color: '#F97316',
                  area: true,
                  showMark: false,
                  curve: 'natural',
                },
                {
                  data: series.agents,
                  label: 'Agents',
                  color: '#8B5CF6',
                  area: true,
                  showMark: false,
                  curve: 'natural',
                },
              ]}
              height={220}
              margin={{ top: 10, bottom: 20, left: 10, right: 10 }}
              hideLegend
              sx={{
                '& .MuiAreaElement-root': { fillOpacity: 0.12 },
                '& .MuiLineElement-root': { strokeWidth: 2 },
              }}
            />
          </Box>
          <Stack direction="row" spacing={2.5} justifyContent="center" sx={{ mt: 0.5 }}>
            {[
              { label: 'Throughput', color: '#14B8A6' },
              { label: 'Alerts', color: '#F97316' },
              { label: 'Agents', color: '#8B5CF6' },
            ].map((item) => (
              <Stack key={item.label} direction="row" spacing={0.75} alignItems="center">
                <Box sx={{ width: 8, height: 8, borderRadius: '2px', bgcolor: item.color }} />
                <Typography variant="caption" color="text.secondary">
                  {item.label}
                </Typography>
              </Stack>
            ))}
          </Stack>
        </>
      )}
    </DashboardCard>
  );
}
