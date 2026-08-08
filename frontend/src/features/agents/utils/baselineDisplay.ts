import { DeviceBaselineItem } from '../../twin/types/deviceBaseline';

/** Parenthesized ps/kernel names, e.g. "(ps)", "(lsappinfo)". */
const PAREN_NAME = /^\([^)]+\)$/;

/** Short CLI utilities the agent/OS spawn constantly — not user apps. */
const NOISE_EXACT = new Set([
  'ps',
  'ioreg',
  'plutil',
  'sw_vers',
  'lsappinfo',
  'uname',
  'sysctl',
  'defaults',
  'launchctl',
  'csrutil',
  'log',
  'osascript',
]);

/** Substrings that mark helpers / sandboxed workers / agents. */
const NOISE_SUBSTRINGS = [
  'helper',
  'worker',
  'mdworker',
  'taskgated',
  'sandbox',
  'xpcproxy',
  'modelcatalog',
  'biomesync',
  'mediaanalysis',
  'generativeexperience',
  'trustedge-agent',
];

/**
 * macOS background daemons usually end with "d" (contactsd, keybagd).
 * Keep short names and known shells/tools that happen to end with "d".
 */
const DAEMON_SUFFIX_ALLOW = new Set([
  'find',
  'head',
  'tail',
  'word',
  'sed',
  'awk',
  'zsh',
  'bash',
  'sh',
  'fish',
  'dash',
  'tmux',
  'screen',
  'node',
  'python',
  'python3',
  'ruby',
  'perl',
  'java',
  'docker',
  'podman',
  'kubectl',
  'git',
  'ssh',
  'scp',
  'curl',
  'wget',
  'chrome',
  'google',
  'firefox',
  'safari',
  'edge',
  'code',
  'cursor',
  'terminal',
  'iterm2',
  'warp',
]);

export function isBaselineNoise(item: DeviceBaselineItem): boolean {
  if (item.behavior_kind !== 'process_comm') {
    // temp_path / binary_mismatch are already high-signal.
    return false;
  }
  const key = (item.behavior_key || '').trim().toLowerCase();
  if (!key) return true;
  if (PAREN_NAME.test(key)) return true;
  if (NOISE_EXACT.has(key)) return true;
  if (NOISE_SUBSTRINGS.some((s) => key.includes(s))) return true;
  if (/^[a-z0-9_-]{5,}d$/.test(key) && !DAEMON_SUFFIX_ALLOW.has(key)) {
    return true;
  }
  if (/^[a-z0-9_-]+d-[a-z0-9_-]+$/.test(key)) {
    // e.g. mediaanalysisd-access
    return true;
  }
  return false;
}

export function sortBaselineItems(items: DeviceBaselineItem[]): DeviceBaselineItem[] {
  return [...items].sort((a, b) => {
    const aTs = Date.parse(a.last_seen_at || a.first_seen_at || '') || 0;
    const bTs = Date.parse(b.last_seen_at || b.first_seen_at || '') || 0;
    if (bTs !== aTs) return bTs - aTs;
    if (b.count !== a.count) return b.count - a.count;
    return a.behavior_key.localeCompare(b.behavior_key);
  });
}

function matchesBaselineSearch(item: DeviceBaselineItem, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const display = displayBaselineKey(item.behavior_key).toLowerCase();
  const key = (item.behavior_key || '').toLowerCase();
  const kind = (item.behavior_kind || '').toLowerCase();
  return display.includes(q) || key.includes(q) || kind.includes(q);
}

export function prepareBaselineItems(
  items: DeviceBaselineItem[],
  options?: { includeSystem?: boolean; query?: string }
): DeviceBaselineItem[] {
  const includeSystem = Boolean(options?.includeSystem);
  const query = options?.query || '';
  let filtered = includeSystem ? items : items.filter((item) => !isBaselineNoise(item));
  if (query.trim()) {
    filtered = filtered.filter((item) => matchesBaselineSearch(item, query));
  }
  return sortBaselineItems(filtered);
}

/** Friendlier label for a few known process keys. */
export function displayBaselineKey(key: string): string {
  const lower = (key || '').trim().toLowerCase();
  if (lower === 'google' || lower === 'google chrome') return 'Chrome';
  if (lower === 'zsh' || lower === 'bash' || lower === 'fish') return `Terminal (${key})`;
  if (lower === 'iterm2') return 'iTerm';
  if (lower === 'code') return 'VS Code';
  if (lower === 'mail') return 'Mail';
  return key;
}
