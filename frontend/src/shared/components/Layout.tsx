import { ReactNode } from 'react';
import type {} from '@mui/x-charts/themeAugmentation';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import AppNavbar from '../../features/dashboard/components/AppNavbar';
import SideMenu from '../../features/dashboard/components/SideMenu';
import AppTheme from '../theme/AppTheme';
import { chartsCustomizations } from '../../features/dashboard/theme/customizations';

const xThemeComponents = {
  ...chartsCustomizations,
};

interface LayoutProps {
  children: ReactNode;
  disableCustomTheme?: boolean;
}

export default function Layout({ children, disableCustomTheme }: LayoutProps) {
  return (
    <AppTheme disableCustomTheme={disableCustomTheme} themeComponents={xThemeComponents}>
      <CssBaseline enableColorScheme />
      <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
        <SideMenu />
        <AppNavbar />
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            backgroundColor: 'background.default',
            overflow: 'auto',
            minHeight: '100vh',
          }}
        >
          <Stack
            spacing={0}
            sx={{
              alignItems: 'stretch',
              px: { xs: 2, md: 3.5 },
              pt: { xs: 9, md: 3 },
              pb: 5,
              maxWidth: 1440,
              mx: 'auto',
              width: '100%',
            }}
          >
            {children}
          </Stack>
        </Box>
      </Box>
    </AppTheme>
  );
}
