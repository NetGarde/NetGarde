import type { AiSessionSummary } from '../../twin/types/aiActivity';

export function formatDurationMs(ms: number | null | undefined): string {
  if (ms == null || ms < 0) return '—';
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ${sec % 60}s`;
  const hr = Math.floor(min / 60);
  return `${hr}h ${min % 60}m`;
}

export function appDisplayName(app: string): string {
  const map: Record<string, string> = {
    cursor: 'Cursor',
    claude: 'Claude',
    vscode: 'VS Code',
    windsurf: 'Windsurf',
    continue: 'Continue',
    cline: 'Cline',
    codex: 'Codex',
    chatgpt: 'ChatGPT',
    aider: 'Aider',
  };
  return map[app] || app.replace(/_/g, ' ');
}

export function riskTone(score: number): 'error' | 'warning' | 'info' | 'default' {
  if (score >= 75) return 'error';
  if (score >= 50) return 'warning';
  if (score > 0) return 'info';
  return 'default';
}

export function sessionSubtitle(session: AiSessionSummary): string {
  const parts = [
    `${session.counters.tool_executions} tools`,
    `${session.counters.network_connections} net`,
    `${session.process_count || session.counters.process_count} procs`,
  ];
  if (session.finding_count) parts.push(`${session.finding_count} findings`);
  return parts.join(' · ');
}

export function extractSessionIdFromDetail(detail: string | null | undefined): string | null {
  if (!detail) return null;
  try {
    const parsed = JSON.parse(detail) as { session_id?: string };
    const sid = (parsed.session_id || '').trim();
    return sid || null;
  } catch {
    return null;
  }
}
