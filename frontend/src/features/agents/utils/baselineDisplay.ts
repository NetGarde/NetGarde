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
    if (b.count !== a.count) return b.count - a.count;
    const kindCmp = a.behavior_kind.localeCompare(b.behavior_kind);
    if (kindCmp !== 0) return kindCmp;
    return a.behavior_key.localeCompare(b.behavior_key);
  });
}

export function prepareBaselineItems(
  items: DeviceBaselineItem[],
  options?: { includeSystem?: boolean }
): DeviceBaselineItem[] {
  const includeSystem = Boolean(options?.includeSystem);
  const filtered = includeSystem ? items : items.filter((item) => !isBaselineNoise(item));
  return sortBaselineItems(filtered);
}

/** Friendlier label for a few known process keys. */
export function displayBaselineKey(key: string): string {
  const lower = (key || '').trim().toLowerCase();
  if (lower === 'google' || lower === 'google chrome') return 'Chrome';
  if (lower === 'zsh' || lower === 'bash' || lower === 'fish') return `Terminal (${key})`;
  if (lower === 'iterm2') return 'iTerm';
  if (lower === 'code') return 'VS Code';
  return key;
}
