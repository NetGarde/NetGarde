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

/** Compact, readable pin label — avoids truncating "26 connections on 443". */
export function formatPinLabel(node: NetworkMapNode, flowViewMode: boolean): string | null {
  if (node.type === 'port') {
    return `:${node.label}`;
  }
  if (node.type === 'flow_summary') {
    const match = node.label.match(/^(\d+)\s+connections?\s+on\s+(\d+)$/i);
    if (match) {
      return `${match[1]} sessions · :${match[2]}`;
    }
    return shortenLabel(node.label, 20);
  }
  if (node.type === 'flow_more') {
    return node.label;
  }
  if (node.type === 'flow') {
    return shortenLabel(node.label, 18);
  }
  if (flowViewMode && node.type === 'gateway') {
    return node.label;
  }
  if (node.type === 'tunnel' || node.type === 'policy') {
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
  height: 18,
  fontSize: 9.5,
  fontWeight: 600,
  rx: 9,
  offsetY: 10,
} as const;

const FLOW_LANES = [0.1, 0.26, 0.4, 0.62, 0.84] as const;
const PATH_LANES = [0.08, 0.22, 0.36, 0.5, 0.64, 0.82] as const;
const ATTRIBUTION_LANES = [0.14, 0.5, 0.86] as const;

/** Lane center X positions for force-layout swimlane guides. */
export function semanticLaneXs(mode: 'attribution' | 'path' | 'flow', width: number): number[] {
  const fractions =
    mode === 'flow' ? FLOW_LANES : mode === 'path' ? PATH_LANES : ATTRIBUTION_LANES;
  return fractions.map((f) => f * width);
}
