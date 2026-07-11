import { NetworkMapNode } from '../types/networkMap';
import { shortenLabel } from './layoutNetworkMap';

export interface NodeVisualSpec {
  radius: number;
  iconSize: number;
  showBadge: boolean;
  badgeMonospace: boolean;
}

const DEFAULT_SPEC: NodeVisualSpec = {
  radius: 14,
  iconSize: 14,
  showBadge: false,
  badgeMonospace: false,
};

const SPECS: Partial<Record<NetworkMapNode['type'], NodeVisualSpec>> = {
  device: { radius: 16, iconSize: 15, showBadge: false, badgeMonospace: false },
  app: { radius: 15, iconSize: 14, showBadge: false, badgeMonospace: false },
  domain: { radius: 14, iconSize: 14, showBadge: true, badgeMonospace: false },
  gateway: { radius: 18, iconSize: 16, showBadge: true, badgeMonospace: false },
  port: { radius: 17, iconSize: 15, showBadge: true, badgeMonospace: true },
  flow: { radius: 14, iconSize: 13, showBadge: true, badgeMonospace: true },
  flow_summary: { radius: 17, iconSize: 15, showBadge: true, badgeMonospace: false },
  flow_more: { radius: 14, iconSize: 13, showBadge: true, badgeMonospace: false },
  tunnel: { radius: 16, iconSize: 15, showBadge: true, badgeMonospace: false },
  policy: { radius: 16, iconSize: 15, showBadge: true, badgeMonospace: false },
};

export function getNodeVisualSpec(type: NetworkMapNode['type']): NodeVisualSpec {
  return SPECS[type] ?? DEFAULT_SPEC;
}

/** Compact, readable pin label — avoids truncating session summaries. */
export function formatPinLabel(node: NetworkMapNode): string | null {
  if (node.type === 'port') {
    // Prefer "HTTPS :443" when already labeled; otherwise ":443".
    if (node.label.includes(':')) {
      return node.label;
    }
    return `:${node.label}`;
  }
  if (node.type === 'flow_summary') {
    const sessionsMatch = node.label.match(/^(\d+)\s+live sessions?$/i);
    if (sessionsMatch) {
      return `${sessionsMatch[1]} sessions`;
    }
    const portMatch = node.label.match(/^(\d+)\s+connections?\s+on\s+(\d+)$/i);
    if (portMatch) {
      return `${portMatch[1]} sessions · :${portMatch[2]}`;
    }
    return shortenLabel(node.label, 20);
  }
  if (node.type === 'flow_more') {
    return node.label;
  }
  if (node.type === 'flow') {
    return shortenLabel(node.label, 18);
  }
  if (node.type === 'gateway') {
    return node.label;
  }
  if (node.type === 'tunnel') {
    return shortenLabel(node.label, 14);
  }
  return null;
}

/** Approximate badge width for SVG pill labels (px). */
export function estimateBadgeWidth(label: string, monospace = false): number {
  const charW = monospace ? 6.2 : 5.6;
  return Math.min(132, Math.max(44, label.length * charW + 16));
}

export const GRAPH_BADGE = {
  height: 16,
  fontSize: 10,
  fontWeight: 500,
  rx: 2,
  offsetY: 8,
} as const;

const FLOW_LANES = [0.1, 0.26, 0.4, 0.62, 0.84] as const;
const PATH_LANES = [0.08, 0.22, 0.36, 0.5, 0.64, 0.82] as const;
const ATTRIBUTION_LANES = [0.14, 0.5, 0.86] as const;

export const UNIFIED_LANES = [0.08, 0.2, 0.32, 0.44, 0.56, 0.68, 0.82] as const;

/** Lane center X positions for force-layout swimlane guides. */
export function semanticLaneXs(mode: 'attribution' | 'path' | 'flow' | 'unified', width: number): number[] {
  const fractions =
    mode === 'unified'
      ? UNIFIED_LANES
      : mode === 'flow'
        ? FLOW_LANES
        : mode === 'path'
          ? PATH_LANES
          : ATTRIBUTION_LANES;
  return fractions.map((f) => f * width);
}
