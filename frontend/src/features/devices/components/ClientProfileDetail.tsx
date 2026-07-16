import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import { Device } from '../types/device';

interface ClientProfileDetailProps {
  device: Device;
}

export default function ClientProfileDetail({ device }: ClientProfileDetailProps) {
  const label = device.hostname || device.external_id;

  return (
    <Paper variant="outlined" sx={{ p: 3, minHeight: 400 }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="h5">{label}</Typography>
          <Typography variant="body2" color="text.secondary">
            {device.external_id}
            {device.mac_address ? ` · ${device.mac_address}` : ''}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Source: {device.source}
          </Typography>
        </Box>
      </Stack>
    </Paper>
  );
}
