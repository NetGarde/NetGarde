import Box from '@mui/material/Box';
import type { BoxProps } from '@mui/material/Box';

type TrustEdgeLogoProps = {
  size?: number;
} & Omit<BoxProps, 'component' | 'src' | 'alt'>;

/** Brand mark from docs/assets/trustedge-icon.svg (served from public/). */
export default function TrustEdgeLogo({ size = 28, sx, ...rest }: TrustEdgeLogoProps) {
  return (
    <Box
      component="img"
      src={`${process.env.PUBLIC_URL}/trustedge-icon.svg`}
      alt=""
      width={size}
      height={size}
      sx={{
        display: 'block',
        flexShrink: 0,
        width: size,
        height: size,
        ...sx,
      }}
      {...rest}
    />
  );
}
