import type { Theme } from '@mui/material/styles';
import type { SxProps } from '@mui/material/styles';
import { alpha } from '@mui/material/styles';

export const NAVBAR_HEIGHT = 56;

/** Top bar surface — white like the sidebar (analytics dashboard look). */
export function navbarBackground(theme: Theme): string {
  return (theme.vars || theme).palette.background.paper;
}

export function navbarBorderColor(theme: Theme): string {
  return theme.palette.divider;
}

export function navAccentColor(theme: Theme): string {
  return theme.palette.primary.main;
}

export function navbarIconButtonSx(theme: Theme): SxProps<Theme> {
  return {
    color: theme.palette.text.secondary,
    '&:hover': {
      backgroundColor: theme.palette.action.hover,
      color: theme.palette.text.primary,
    },
  };
}

export function navbarColorModeButtonSx(theme: Theme): SxProps<Theme> {
  return {
    ...navbarIconButtonSx(theme),
    border: '1px solid',
    borderColor: theme.palette.divider,
  };
}

export function sidebarNavItemSx(theme: Theme, nested = false): SxProps<Theme> {
  return {
    minHeight: 36,
    borderRadius: '8px',
    px: 1.25,
    py: 0.75,
    mx: 0.75,
    mb: 0.25,
    ...(nested ? { ml: 1.5 } : {}),
    position: 'relative',
    '&.Mui-selected': {
      backgroundColor: theme.palette.mode === 'dark' ? alpha(theme.palette.common.white, 0.08) : '#F3F4F6',
      '&:hover': {
        backgroundColor: theme.palette.mode === 'dark' ? alpha(theme.palette.common.white, 0.12) : '#EBEBED',
      },
      '& .MuiListItemText-primary': {
        color: theme.palette.text.primary,
        fontWeight: 500,
      },
    },
    '&:hover': {
      backgroundColor: theme.palette.action.hover,
    },
  };
}

export function sidebarSectionButtonSx(theme: Theme): SxProps<Theme> {
  return {
    minHeight: 32,
    borderRadius: '8px',
    px: 1.25,
    py: 0.5,
    mx: 0.75,
    mb: 0.25,
    mt: 1,
    '&:hover': {
      backgroundColor: theme.palette.action.hover,
    },
  };
}
