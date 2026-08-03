import { useState } from 'react';
import { styled } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import MuiDrawer, { drawerClasses } from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Link from '@mui/material/Link';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ShieldOutlinedIcon from '@mui/icons-material/ShieldOutlined';
import MenuContent from './MenuContent';
import './SideMenu.css';

const drawerWidth = 248;
const collapsedWidth = 72;

const Drawer = styled(MuiDrawer, {
  shouldForwardProp: (prop) => prop !== 'open',
})<{ open?: boolean }>(({ theme, open }) => ({
  width: open ? drawerWidth : collapsedWidth,
  flexShrink: 0,
  whiteSpace: 'nowrap',
  boxSizing: 'border-box',
  transition: theme.transitions.create('width', {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.enteringScreen,
  }),
  [`& .${drawerClasses.paper}`]: {
    width: open ? drawerWidth : collapsedWidth,
    transition: theme.transitions.create('width', {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.enteringScreen,
    }),
    overflowX: 'hidden',
    backgroundColor: (theme.vars || theme).palette.background.paper,
    borderRight: `1px solid ${(theme.vars || theme).palette.divider}`,
    boxShadow: 'none',
  },
}));

export default function SideMenu() {
  const [open, setOpen] = useState(true);

  const handleDrawerToggle = () => {
    setOpen(!open);
  };

  return (
    <Drawer
      variant="permanent"
      open={open}
      sx={{
        display: { xs: 'none', md: 'block' },
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: open ? 'space-between' : 'center',
          px: open ? 2 : 1,
          pt: 2.5,
          pb: 1.5,
          minHeight: 64,
        }}
      >
        {open && (
          <Stack direction="row" spacing={1.25} alignItems="center" sx={{ minWidth: 0 }}>
            <Box
              sx={{
                width: 28,
                height: 28,
                borderRadius: '8px',
                bgcolor: 'primary.main',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <ShieldOutlinedIcon sx={{ color: '#fff', fontSize: 16 }} />
            </Box>
            <Typography
              variant="subtitle1"
              sx={{
                fontWeight: 700,
                fontSize: '1rem',
                color: 'text.primary',
                letterSpacing: '-0.02em',
              }}
            >
              TrustEdge
            </Typography>
          </Stack>
        )}
        <IconButton
          onClick={handleDrawerToggle}
          size="small"
          sx={{
            color: 'text.secondary',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: '8px',
            width: 28,
            height: 28,
            '&:hover': {
              backgroundColor: 'action.hover',
            },
          }}
        >
          {open ? <ChevronLeftIcon sx={{ fontSize: 18 }} /> : <ChevronRightIcon sx={{ fontSize: 18 }} />}
        </IconButton>
      </Box>

      <Box
        sx={{
          overflow: 'auto',
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <MenuContent open={open} />
      </Box>

      <Stack
        direction="row"
        sx={{
          p: open ? 2 : 1.25,
          gap: 1.25,
          alignItems: 'center',
          justifyContent: open ? 'flex-start' : 'center',
          minHeight: 80,
          borderTop: 1,
          borderColor: 'divider',
        }}
      >
        <Avatar
          sizes="small"
          alt="Admin"
          sx={{
            width: open ? 36 : 32,
            height: open ? 36 : 32,
            bgcolor: 'primary.main',
            fontSize: '0.85rem',
            fontWeight: 600,
          }}
        >
          TE
        </Avatar>
        {open && (
          <Box sx={{ mr: 'auto', flex: 1, minWidth: 0 }}>
            <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.3, color: 'text.primary' }}>
              Admin
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }} noWrap>
              admin@trustedge.local
            </Typography>
            <Link
              component="button"
              variant="caption"
              underline="hover"
              sx={{ color: 'text.secondary', mt: 0.25, display: 'inline-block' }}
            >
              Sign out
            </Link>
          </Box>
        )}
      </Stack>
    </Drawer>
  );
}
