import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { PieChart } from '@mui/x-charts/PieChart';
import DashboardCard from './DashboardCard';
import { useSecurityAlerts } from '../../../twin/hooks/useSecurityAlerts';

const COLORS: Record<string, string> = {
  high: '#EF4444',
  medium: '#F97316',
  low: '#14B8A6',
  unknown: '#6B7280',
};

export default function SeverityDonutCard() {
  const { items, loading } = useSecurityAlerts({ pageSize: 100 });

  const counts: Record<string, number> = {};
  for (const alert of items) {
    const key = (alert.severity || 'unknown').toLowerCase();
    counts[key] = (counts[key] || 0) + 1;
  }

  const data = Object.entries(counts).map(([label, value], id) => ({
    id,
    value,
    label: label.charAt(0).toUpperCase() + label.slice(1),
    color: COLORS[label] || COLORS.unknown,
  }));

  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <DashboardCard title="Alert severity">
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress size={24} />
        </Box>
      ) : total === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
          No severity data yet.
        </Typography>
      ) : (
        <Stack direction="row" alignItems="center" spacing={1} sx={{ flex: 1 }}>
          <Box sx={{ width: 140, height: 140, position: 'relative', flexShrink: 0 }}>
            <PieChart
              series={[
                {
                  data,
                  innerRadius: 42,
                  outerRadius: 64,
                  paddingAngle: 2,
                  cornerRadius: 3,
                  cx: 70,
                  cy: 70,
                },
              ]}
              width={140}
              height={140}
              hideLegend
            />
            <Box
              sx={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                pointerEvents: 'none',
              }}
            >
              <Typography sx={{ fontWeight: 700, fontSize: '1.1rem' }}>{total}</Typography>
            </Box>
          </Box>
          <Stack spacing={1} sx={{ flex: 1, minWidth: 0 }}>
            {data.map((d) => (
              <Stack key={d.label} direction="row" spacing={1} alignItems="center">
                <Box sx={{ width: 8, height: 8, borderRadius: '2px', bgcolor: d.color, flexShrink: 0 }} />
                <Typography variant="caption" color="text.secondary" sx={{ flex: 1 }} noWrap>
                  {d.label}
                </Typography>
                <Typography variant="caption" sx={{ fontWeight: 600 }}>
                  {Math.round((d.value / total) * 100)}%
                </Typography>
              </Stack>
            ))}
          </Stack>
        </Stack>
      )}
    </DashboardCard>
  );
}
