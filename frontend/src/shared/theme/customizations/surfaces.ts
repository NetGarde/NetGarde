import { alpha, Theme, Components } from '@mui/material/styles';
import { gray } from '../themePrimitives';

export const surfacesCustomizations: Components<Theme> = {
  MuiAccordion: {
    defaultProps: {
      elevation: 0,
      disableGutters: true,
    },
    styleOverrides: {
      root: ({ theme }) => ({
        padding: 4,
        overflow: 'clip',
        backgroundColor: (theme.vars || theme).palette.background.default,
        border: '1px solid',
        borderColor: (theme.vars || theme).palette.divider,
        ':before': {
          backgroundColor: 'transparent',
        },
        '&:not(:last-of-type)': {
          borderBottom: 'none',
        },
        '&:first-of-type': {
          borderTopLeftRadius: (theme.vars || theme).shape.borderRadius,
          borderTopRightRadius: (theme.vars || theme).shape.borderRadius,
        },
        '&:last-of-type': {
          borderBottomLeftRadius: (theme.vars || theme).shape.borderRadius,
          borderBottomRightRadius: (theme.vars || theme).shape.borderRadius,
        },
      }),
    },
  },
  MuiAccordionSummary: {
    styleOverrides: {
      root: ({ theme }) => ({
        border: 'none',
        borderRadius: 8,
        '&:hover': { backgroundColor: gray[50] },
        '&:focus-visible': { backgroundColor: 'transparent' },
        ...theme.applyStyles('dark', {
          '&:hover': { backgroundColor: gray[800] },
        }),
      }),
    },
  },
  MuiAccordionDetails: {
    styleOverrides: {
      root: { mb: 20, border: 'none' },
    },
  },
  MuiPaper: {
    defaultProps: {
      elevation: 0,
    },
    styleOverrides: {
      root: ({ theme }) => ({
        backgroundImage: 'none',
        variants: [
          {
            props: { variant: 'outlined' },
            style: {
              border: `1px solid ${(theme.vars || theme).palette.divider}`,
              borderRadius: 12,
              backgroundColor: (theme.vars || theme).palette.background.paper,
              boxShadow: '0px 1px 2px rgba(16, 24, 40, 0.04)',
              ...theme.applyStyles('dark', {
                boxShadow: 'none',
              }),
            },
          },
        ],
      }),
    },
  },
  MuiCard: {
    styleOverrides: {
      root: ({ theme }) => {
        return {
          padding: 20,
          gap: 16,
          transition: 'all 100ms ease',
          backgroundColor: (theme.vars || theme).palette.background.paper,
          borderRadius: 12,
          border: `1px solid ${(theme.vars || theme).palette.divider}`,
          boxShadow: '0px 1px 2px rgba(16, 24, 40, 0.04)',
          ...theme.applyStyles('dark', {
            backgroundColor: gray[800],
            boxShadow: 'none',
          }),
          variants: [
            {
              props: {
                variant: 'outlined',
              },
              style: {
                border: `1px solid ${(theme.vars || theme).palette.divider}`,
                boxShadow: '0px 1px 2px rgba(16, 24, 40, 0.04)',
                background: (theme.vars || theme).palette.background.paper,
                ...theme.applyStyles('dark', {
                  background: alpha(gray[900], 0.4),
                  boxShadow: 'none',
                }),
              },
            },
          ],
        };
      },
    },
  },
  MuiCardContent: {
    styleOverrides: {
      root: {
        padding: 0,
        '&:last-child': { paddingBottom: 0 },
      },
    },
  },
  MuiCardHeader: {
    styleOverrides: {
      root: {
        padding: 0,
      },
    },
  },
  MuiCardActions: {
    styleOverrides: {
      root: {
        padding: 0,
      },
    },
  },
};
