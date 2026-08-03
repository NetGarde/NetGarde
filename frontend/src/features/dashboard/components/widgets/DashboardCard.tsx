import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import { ReactNode } from 'react';

interface DashboardCardProps {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  sx?: object;
}

export default function DashboardCard({ title, action, children, sx }: DashboardCardProps) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2.5,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        ...sx,
      }}
    >
      <Typography
        variant="subtitle2"
        sx={{
          fontWeight: 600,
          color: 'text.primary',
          mb: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1,
        }}
      >
        {title}
        {action}
      </Typography>
      {children}
    </Paper>
  );
}
