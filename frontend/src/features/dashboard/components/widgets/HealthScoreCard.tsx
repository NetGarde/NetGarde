import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import { Gauge, gaugeClasses } from '@mui/x-charts/Gauge';
import DevicesIcon from '@mui/icons-material/Devices';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import SpeedIcon from '@mui/icons-material/Speed';
import HubIcon from '@mui/icons-material/Hub';
import DashboardCard from './DashboardCard';
import { useNetworkOverview } from '../../hooks/useNetworkOverview';

function scoreLabel(score: number): string {
  if (score >= 90) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 50) return 'Fair';
  return 'At risk';
}

export default function HealthScoreCard() {
  const { data, loading } = useNetworkOverview(60);
  const stats = data?.stats;

  const alertPenalty = Math.min(60, (stats?.alerts_total ?? 0) * 8);
  const agentBonus = Math.min(20, (stats?.reporting_clients ?? 0) * 4);
  const score = Math.max(0, Math.min(100, 80 - alertPenalty + agentBonus));
  const label = scoreLabel(score);

  const metrics = [
    {
      icon: <DevicesIcon sx={{ fontSize: 16, color: 'text.secondary' }} />,
      label: 'Live agents',
      value: stats?.reporting_clients ?? '—',
    },
    {
      icon: <WarningAmberIcon sx={{ fontSize: 16, color: 'text.secondary' }} />,
      label: 'Alerts',
      value: stats?.alerts_total ?? '—',
    },
    {
      icon: <SpeedIcon sx={{ fontSize: 16, color: 'text.secondary' }} />,
      label: 'Throughput',
      value: stats ? `${stats.live_total_mib_per_sec.toFixed(1)} MiB/s` : '—',
    },
    {
      icon: <HubIcon sx={{ fontSize: 16, color: 'text.secondary' }} />,
      label: 'Peak',
      value: stats ? `${stats.peak_mib_per_sec.toFixed(1)} MiB/s` : '—',
    },
  ];

  return (
    <DashboardCard title="Network health">
      {loading && !data ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress size={28} />
        </Box>
      ) : (
        <>
          <Box sx={{ display: 'flex', justifyContent: 'center', position: 'relative', mb: 1 }}>
            <Gauge
              width={180}
              height={120}
              value={score}
              startAngle={-110}
              endAngle={110}
              sx={{
                [`& .${gaugeClasses.valueText}`]: { display: 'none' },
                [`& .${gaugeClasses.valueArc}`]: { fill: 'var(--template-palette-primary-main, #14B8A6)' },
                [`& .${gaugeClasses.referenceArc}`]: { fill: '#E5E7EB' },
              }}
            />
            <Box
              sx={{
                position: 'absolute',
                top: '52%',
                left: '50%',
                transform: 'translate(-50%, -40%)',
                textAlign: 'center',
              }}
            >
              <Typography sx={{ fontSize: '1.75rem', fontWeight: 700, lineHeight: 1, color: 'text.primary' }}>
                {score}
              </Typography>
              <Typography variant="caption" sx={{ color: 'primary.main', fontWeight: 600 }}>
                {label}
              </Typography>
            </Box>
          </Box>

          <Stack spacing={1.25} sx={{ mt: 1 }}>
            {metrics.map((m) => (
              <Stack key={m.label} direction="row" alignItems="center" justifyContent="space-between">
                <Stack direction="row" spacing={1} alignItems="center">
                  {m.icon}
                  <Typography variant="body2" color="text.secondary">
                    {m.label}
                  </Typography>
                </Stack>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {m.value}
                </Typography>
              </Stack>
            ))}
          </Stack>
        </>
      )}
    </DashboardCard>
  );
}
