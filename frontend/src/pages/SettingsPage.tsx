import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Paper from '@mui/material/Paper';

export default function SettingsPage() {
  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
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
        Settings
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
        Product configuration for TrustEdge operators.
      </Typography>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Alert severity="info" variant="outlined">
          Settings UI coming soon. Tokens and environment live in{' '}
          <code>/etc/trustedge/backend.env</code> on the host for now.
        </Alert>
      </Paper>
    </Box>
  );
}
