import { ReactElement } from 'react';
import GroupsIcon from '@mui/icons-material/Groups';
import VideocamIcon from '@mui/icons-material/Videocam';
import ForumIcon from '@mui/icons-material/Forum';
import LanguageIcon from '@mui/icons-material/Language';
import PublicIcon from '@mui/icons-material/Public';
import CodeIcon from '@mui/icons-material/Code';
import MailOutlineIcon from '@mui/icons-material/MailOutline';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import TerminalIcon from '@mui/icons-material/Terminal';
import AppsIcon from '@mui/icons-material/Apps';
import DnsIcon from '@mui/icons-material/Dns';
import ComputerIcon from '@mui/icons-material/Computer';
import BlockIcon from '@mui/icons-material/Block';
import VpnLockIcon from '@mui/icons-material/VpnLock';
import RouterIcon from '@mui/icons-material/Router';
import GavelIcon from '@mui/icons-material/Gavel';
import SettingsEthernetIcon from '@mui/icons-material/SettingsEthernet';
import HubIcon from '@mui/icons-material/Hub';
import MoreHorizIcon from '@mui/icons-material/MoreHoriz';
import TagIcon from '@mui/icons-material/Tag';
import WifiIcon from '@mui/icons-material/Wifi';

export interface AppIconStyle {
  icon: ReactElement;
  color: string;
  bg: string;
}

/** Muted ops-console palette (slate / steel — not neon). */
const SLATE = '#64748B';
const SLATE_BG = 'rgba(100, 116, 139, 0.1)';
const STEEL = '#475569';
const STEEL_BG = 'rgba(71, 85, 105, 0.12)';
const INK = '#334155';
const INK_BG = 'rgba(51, 65, 85, 0.1)';
const DANGER = '#B91C1C';
const DANGER_BG = 'rgba(185, 28, 28, 0.08)';

const APP_ICON_MAP: Record<string, AppIconStyle> = {
  microsoft_teams: { icon: <GroupsIcon fontSize="small" />, color: STEEL, bg: STEEL_BG },
  zoom: { icon: <VideocamIcon fontSize="small" />, color: STEEL, bg: STEEL_BG },
  slack: { icon: <ForumIcon fontSize="small" />, color: STEEL, bg: STEEL_BG },
  safari: { icon: <PublicIcon fontSize="small" />, color: STEEL, bg: STEEL_BG },
  google_chrome: { icon: <LanguageIcon fontSize="small" />, color: STEEL, bg: STEEL_BG },
  microsoft_edge: { icon: <LanguageIcon fontSize="small" />, color: STEEL, bg: STEEL_BG },
  vscode: { icon: <CodeIcon fontSize="small" />, color: STEEL, bg: STEEL_BG },
  cursor: { icon: <TerminalIcon fontSize="small" />, color: STEEL, bg: STEEL_BG },
  apple_mail: { icon: <MailOutlineIcon fontSize="small" />, color: STEEL, bg: STEEL_BG },
  finder: { icon: <FolderOpenIcon fontSize="small" />, color: STEEL, bg: STEEL_BG },
};

export function getAppIconStyle(slug?: string | null): AppIconStyle {
  if (slug && APP_ICON_MAP[slug]) {
    return APP_ICON_MAP[slug];
  }
  return {
    icon: <AppsIcon fontSize="small" />,
    color: SLATE,
    bg: SLATE_BG,
  };
}

export function getDeviceIconStyle(): AppIconStyle {
  return {
    icon: <ComputerIcon fontSize="small" />,
    color: INK,
    bg: INK_BG,
  };
}

export function getDomainIconStyle(blocked?: boolean | null): AppIconStyle {
  if (blocked) {
    return {
      icon: <BlockIcon fontSize="small" />,
      color: DANGER,
      bg: DANGER_BG,
    };
  }
  return {
    icon: <DnsIcon fontSize="small" />,
    color: STEEL,
    bg: STEEL_BG,
  };
}

export function getInfraIconStyle(
  type: 'tunnel' | 'gateway' | 'policy',
  label?: string,
): AppIconStyle {
  if (type === 'tunnel') {
    const isLan =
      label != null &&
      /wi-?fi|ethernet|cellular|network/i.test(label);
    return {
      icon: isLan ? <WifiIcon fontSize="small" /> : <VpnLockIcon fontSize="small" />,
      color: STEEL,
      bg: STEEL_BG,
    };
  }
  if (type === 'gateway') {
    return {
      icon: <RouterIcon fontSize="small" />,
      color: STEEL,
      bg: STEEL_BG,
    };
  }
  return {
    icon: <GavelIcon fontSize="small" />,
    color: SLATE,
    bg: SLATE_BG,
  };
}

export function getPortIconStyle(): AppIconStyle {
  return {
    icon: <TagIcon fontSize="small" />,
    color: STEEL,
    bg: STEEL_BG,
  };
}

export function getFlowSummaryIconStyle(): AppIconStyle {
  return {
    icon: <HubIcon fontSize="small" />,
    color: STEEL,
    bg: STEEL_BG,
  };
}

export function getFlowMoreIconStyle(): AppIconStyle {
  return {
    icon: <MoreHorizIcon fontSize="small" />,
    color: SLATE,
    bg: SLATE_BG,
  };
}

export function getFlowIconStyle(): AppIconStyle {
  return {
    icon: <SettingsEthernetIcon fontSize="small" />,
    color: STEEL,
    bg: STEEL_BG,
  };
}

export function getNodeIconStyle(node: {
  type: string;
  app_slug?: string | null;
  blocked?: boolean | null;
  label?: string | null;
}): AppIconStyle {
  if (node.type === 'device') {
    return getDeviceIconStyle();
  }
  if (node.type === 'app') {
    return getAppIconStyle(node.app_slug);
  }
  if (node.type === 'domain') {
    return getDomainIconStyle(node.blocked);
  }
  if (node.type === 'flow' || node.type === 'flow_summary' || node.type === 'flow_more') {
    if (node.type === 'flow_summary') {
      return getFlowSummaryIconStyle();
    }
    if (node.type === 'flow_more') {
      return getFlowMoreIconStyle();
    }
    return getFlowIconStyle();
  }
  if (node.type === 'port') {
    return getPortIconStyle();
  }
  if (node.type === 'tunnel' || node.type === 'gateway' || node.type === 'policy') {
    return getInfraIconStyle(node.type, node.label ?? undefined);
  }
  return getAppIconStyle(null);
}
