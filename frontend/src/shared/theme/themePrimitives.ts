import { createTheme, alpha, PaletteMode, Shadows } from '@mui/material/styles';

declare module '@mui/material/Paper' {
  interface PaperPropsVariantOverrides {
    highlighted: true;
  }
}
declare module '@mui/material/styles' {
  interface ColorRange {
    50: string;
    100: string;
    200: string;
    300: string;
    400: string;
    500: string;
    600: string;
    700: string;
    800: string;
    900: string;
  }

  interface PaletteColor extends ColorRange {}

  interface Palette {
    baseShadow: string;
  }
}

const defaultTheme = createTheme();

const customShadows: Shadows = [...defaultTheme.shadows];

/** Teal accent matching the analytics dashboard look. */
export const brand = {
  50: 'hsl(168, 76%, 96%)',
  100: 'hsl(168, 70%, 90%)',
  200: 'hsl(168, 65%, 78%)',
  300: 'hsl(172, 55%, 55%)',
  400: 'hsl(173, 58%, 39%)',
  500: 'hsl(175, 70%, 32%)',
  600: 'hsl(176, 72%, 26%)',
  700: 'hsl(177, 75%, 20%)',
  800: 'hsl(178, 80%, 14%)',
  900: 'hsl(179, 84%, 10%)',
};

export const gray = {
  50: 'hsl(220, 20%, 97%)',
  100: 'hsl(220, 16%, 94%)',
  200: 'hsl(220, 14%, 90%)',
  300: 'hsl(220, 12%, 82%)',
  400: 'hsl(220, 10%, 64%)',
  500: 'hsl(220, 9%, 46%)',
  600: 'hsl(220, 10%, 36%)',
  700: 'hsl(220, 13%, 26%)',
  800: 'hsl(220, 18%, 16%)',
  900: 'hsl(220, 22%, 10%)',
};

export const green = {
  50: 'hsl(145, 60%, 96%)',
  100: 'hsl(145, 55%, 90%)',
  200: 'hsl(145, 50%, 78%)',
  300: 'hsl(145, 45%, 58%)',
  400: 'hsl(145, 50%, 42%)',
  500: 'hsl(145, 55%, 32%)',
  600: 'hsl(145, 60%, 26%)',
  700: 'hsl(145, 65%, 20%)',
  800: 'hsl(145, 70%, 14%)',
  900: 'hsl(145, 75%, 10%)',
};

export const orange = {
  50: 'hsl(28, 100%, 97%)',
  100: 'hsl(28, 95%, 90%)',
  200: 'hsl(28, 90%, 78%)',
  300: 'hsl(25, 90%, 62%)',
  400: 'hsl(22, 90%, 50%)',
  500: 'hsl(20, 90%, 42%)',
  600: 'hsl(18, 90%, 34%)',
  700: 'hsl(16, 90%, 26%)',
  800: 'hsl(14, 90%, 18%)',
  900: 'hsl(12, 90%, 12%)',
};

export const red = {
  50: 'hsl(0, 100%, 97%)',
  100: 'hsl(0, 92%, 90%)',
  200: 'hsl(0, 94%, 80%)',
  300: 'hsl(0, 90%, 65%)',
  400: 'hsl(0, 84%, 50%)',
  500: 'hsl(0, 80%, 42%)',
  600: 'hsl(0, 78%, 34%)',
  700: 'hsl(0, 76%, 26%)',
  800: 'hsl(0, 74%, 18%)',
  900: 'hsl(0, 72%, 12%)',
};

export const purple = {
  50: 'hsl(262, 80%, 96%)',
  100: 'hsl(262, 70%, 90%)',
  200: 'hsl(262, 60%, 78%)',
  300: 'hsl(262, 55%, 64%)',
  400: 'hsl(262, 52%, 52%)',
  500: 'hsl(262, 55%, 42%)',
  600: 'hsl(262, 58%, 34%)',
  700: 'hsl(262, 60%, 26%)',
  800: 'hsl(262, 62%, 18%)',
  900: 'hsl(262, 65%, 12%)',
};

export const getDesignTokens = (mode: PaletteMode) => {
  customShadows[1] =
    mode === 'dark'
      ? 'hsla(220, 30%, 5%, 0.7) 0px 4px 16px 0px, hsla(220, 25%, 10%, 0.8) 0px 8px 16px -5px'
      : '0px 1px 2px rgba(16, 24, 40, 0.04), 0px 1px 3px rgba(16, 24, 40, 0.06)';

  return {
    palette: {
      mode,
      primary: {
        light: brand[200],
        main: brand[400],
        dark: brand[700],
        contrastText: '#ffffff',
        ...(mode === 'dark' && {
          contrastText: brand[50],
          light: brand[300],
          main: brand[400],
          dark: brand[700],
        }),
      },
      info: {
        light: brand[100],
        main: brand[300],
        dark: brand[600],
        contrastText: gray[50],
        ...(mode === 'dark' && {
          contrastText: brand[300],
          light: brand[500],
          main: brand[700],
          dark: brand[900],
        }),
      },
      warning: {
        light: orange[300],
        main: orange[400],
        dark: orange[800],
        ...(mode === 'dark' && {
          light: orange[400],
          main: orange[500],
          dark: orange[700],
        }),
      },
      error: {
        light: red[300],
        main: red[400],
        dark: red[800],
        ...(mode === 'dark' && {
          light: red[400],
          main: red[500],
          dark: red[700],
        }),
      },
      success: {
        light: green[300],
        main: green[400],
        dark: green[800],
        ...(mode === 'dark' && {
          light: green[400],
          main: green[500],
          dark: green[700],
        }),
      },
      grey: {
        ...gray,
      },
      divider: mode === 'dark' ? alpha(gray[700], 0.6) : '#E5E7EB',
      background: {
        default: '#F7F8FA',
        paper: '#FFFFFF',
        ...(mode === 'dark' && { default: gray[900], paper: 'hsl(220, 30%, 7%)' }),
      },
      text: {
        primary: '#111827',
        secondary: '#6B7280',
        warning: orange[400],
        ...(mode === 'dark' && { primary: 'hsl(0, 0%, 100%)', secondary: gray[400] }),
      },
      action: {
        hover: alpha(gray[200], 0.5),
        selected: gray[100],
        ...(mode === 'dark' && {
          hover: alpha(gray[600], 0.2),
          selected: alpha(gray[600], 0.3),
        }),
      },
    },
    typography: {
      fontFamily:
        '"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      h1: {
        fontSize: defaultTheme.typography.pxToRem(48),
        fontWeight: 600,
        lineHeight: 1.2,
        letterSpacing: -0.5,
      },
      h2: {
        fontSize: defaultTheme.typography.pxToRem(36),
        fontWeight: 600,
        lineHeight: 1.2,
      },
      h3: {
        fontSize: defaultTheme.typography.pxToRem(30),
        lineHeight: 1.2,
      },
      h4: {
        fontSize: defaultTheme.typography.pxToRem(24),
        fontWeight: 600,
        lineHeight: 1.5,
      },
      h5: {
        fontSize: defaultTheme.typography.pxToRem(20),
        fontWeight: 600,
      },
      h6: {
        fontSize: defaultTheme.typography.pxToRem(18),
        fontWeight: 600,
      },
      subtitle1: {
        fontSize: defaultTheme.typography.pxToRem(18),
      },
      subtitle2: {
        fontSize: defaultTheme.typography.pxToRem(14),
        fontWeight: 500,
      },
      body1: {
        fontSize: defaultTheme.typography.pxToRem(14),
      },
      body2: {
        fontSize: defaultTheme.typography.pxToRem(14),
        fontWeight: 400,
      },
      caption: {
        fontSize: defaultTheme.typography.pxToRem(12),
        fontWeight: 400,
      },
    },
    shape: {
      borderRadius: 10,
    },
    shadows: customShadows,
  };
};

export const colorSchemes = {
  light: {
    palette: {
      primary: {
        light: brand[200],
        main: brand[400],
        dark: brand[700],
        contrastText: '#ffffff',
      },
      info: {
        light: brand[100],
        main: brand[300],
        dark: brand[600],
        contrastText: gray[50],
      },
      warning: {
        light: orange[300],
        main: orange[400],
        dark: orange[800],
      },
      error: {
        light: red[300],
        main: red[400],
        dark: red[800],
      },
      success: {
        light: green[300],
        main: green[400],
        dark: green[800],
      },
      grey: {
        ...gray,
      },
      divider: '#E5E7EB',
      background: {
        default: '#F7F8FA',
        paper: '#FFFFFF',
      },
      text: {
        primary: '#111827',
        secondary: '#6B7280',
        warning: orange[400],
      },
      action: {
        hover: alpha(gray[200], 0.55),
        selected: gray[100],
      },
      baseShadow: '0px 1px 2px rgba(16, 24, 40, 0.04), 0px 1px 3px rgba(16, 24, 40, 0.06)',
    },
  },
  dark: {
    palette: {
      primary: {
        contrastText: brand[50],
        light: brand[300],
        main: brand[400],
        dark: brand[700],
      },
      info: {
        contrastText: brand[300],
        light: brand[500],
        main: brand[700],
        dark: brand[900],
      },
      warning: {
        light: orange[400],
        main: orange[500],
        dark: orange[700],
      },
      error: {
        light: red[400],
        main: red[500],
        dark: red[700],
      },
      success: {
        light: green[400],
        main: green[500],
        dark: green[700],
      },
      grey: {
        ...gray,
      },
      divider: alpha(gray[700], 0.6),
      background: {
        default: gray[900],
        paper: 'hsl(220, 30%, 7%)',
      },
      text: {
        primary: 'hsl(0, 0%, 100%)',
        secondary: gray[400],
      },
      action: {
        hover: alpha(gray[600], 0.2),
        selected: alpha(gray[600], 0.3),
      },
      baseShadow:
        'hsla(220, 30%, 5%, 0.7) 0px 4px 16px 0px, hsla(220, 25%, 10%, 0.8) 0px 8px 16px -5px',
    },
  },
};

export const typography = {
  fontFamily:
    '"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  h1: {
    fontSize: defaultTheme.typography.pxToRem(48),
    fontWeight: 600,
    lineHeight: 1.2,
    letterSpacing: -0.5,
  },
  h2: {
    fontSize: defaultTheme.typography.pxToRem(36),
    fontWeight: 600,
    lineHeight: 1.2,
  },
  h3: {
    fontSize: defaultTheme.typography.pxToRem(30),
    lineHeight: 1.2,
  },
  h4: {
    fontSize: defaultTheme.typography.pxToRem(24),
    fontWeight: 600,
    lineHeight: 1.5,
  },
  h5: {
    fontSize: defaultTheme.typography.pxToRem(20),
    fontWeight: 600,
  },
  h6: {
    fontSize: defaultTheme.typography.pxToRem(18),
    fontWeight: 600,
  },
  subtitle1: {
    fontSize: defaultTheme.typography.pxToRem(18),
  },
  subtitle2: {
    fontSize: defaultTheme.typography.pxToRem(14),
    fontWeight: 500,
  },
  body1: {
    fontSize: defaultTheme.typography.pxToRem(14),
  },
  body2: {
    fontSize: defaultTheme.typography.pxToRem(14),
    fontWeight: 400,
  },
  caption: {
    fontSize: defaultTheme.typography.pxToRem(12),
    fontWeight: 400,
  },
};

export const shape = {
  borderRadius: 10,
};

const defaultShadows: Shadows = [
  'none',
  'var(--template-palette-baseShadow)',
  ...defaultTheme.shadows.slice(2),
];
export const shadows = defaultShadows;
