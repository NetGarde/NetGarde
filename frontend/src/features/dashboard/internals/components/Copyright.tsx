import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import type { TypographyProps } from '@mui/material/Typography';

export default function Copyright(props: TypographyProps) {
  const year = new Date().getFullYear();

  return (
    <Typography
      variant="body2"
      align="center"
      {...props}
      sx={[
        { color: 'text.secondary' },
        ...(Array.isArray(props.sx) ? props.sx : props.sx ? [props.sx] : []),
      ]}
    >
      {'Copyright © '}
      <Box component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>
        TrustEdge
      </Box>
      {` ${year}. Self-hosted security observability.`}
    </Typography>
  );
}
