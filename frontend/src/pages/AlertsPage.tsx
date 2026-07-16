import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Paper from '@mui/material/Paper';

export default function AlertsPage() {
  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Typography component="h1" variant="h5" sx={{ mb: 0.5 }}>
        Alerts
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Detection findings from the rules engine. This page will list active and recent alerts.
      </Typography>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Alert severity="info" variant="outlined">
          Alerts UI coming soon. Backend ingest remains at <code>POST /security/alerts/ingest</code>.
        </Alert>
      </Paper>
    </Box>
  );
}
