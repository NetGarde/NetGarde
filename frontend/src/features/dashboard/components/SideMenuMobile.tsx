import Avatar from '@mui/material/Avatar';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Drawer, { drawerClasses } from '@mui/material/Drawer';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded';
import MenuContent from './MenuContent';
import TrustEdgeLogo from '../../../shared/components/TrustEdgeLogo';

interface SideMenuMobileProps {
  open: boolean;
  toggleDrawer: (newOpen: boolean) => () => void;
}

export default function SideMenuMobile({ open, toggleDrawer }: SideMenuMobileProps) {
  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={toggleDrawer(false)}
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
        [`& .${drawerClasses.paper}`]: {
          backgroundImage: 'none',
          backgroundColor: 'background.paper',
          width: 280,
        },
      }}
    >
      <Stack sx={{ height: '100%' }}>
        <Stack direction="row" sx={{ p: 2, gap: 1.25, alignItems: 'center' }}>
          <TrustEdgeLogo size={28} />
          <Typography sx={{ fontWeight: 700, flex: 1 }}>TrustEdge</Typography>
        </Stack>
        <Divider />
        <Stack sx={{ flexGrow: 1, overflow: 'auto' }}>
          <MenuContent />
        </Stack>
        <Divider />
        <Stack direction="row" spacing={1.25} sx={{ p: 2, alignItems: 'center' }}>
          <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: '0.8rem' }}>TE</Avatar>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              Admin
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap>
              admin@trustedge.local
            </Typography>
          </Box>
        </Stack>
        <Stack sx={{ px: 2, pb: 2 }}>
          <Button variant="outlined" fullWidth startIcon={<LogoutRoundedIcon />} sx={{ textTransform: 'none' }}>
            Sign out
          </Button>
        </Stack>
      </Stack>
    </Drawer>
  );
}
