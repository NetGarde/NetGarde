import type { SvgIconProps } from '@mui/material/SvgIcon';
import SvgIcon from '@mui/material/SvgIcon';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import TerminalIcon from '@mui/icons-material/Terminal';
import MemoryIcon from '@mui/icons-material/Memory';
import ExtensionIcon from '@mui/icons-material/Extension';

/** Cursor brand mark (cube) — fill follows currentColor. */
export function CursorIcon(props: SvgIconProps) {
  return (
    <SvgIcon {...props} viewBox="0 0 49 56">
      <path
        fill="currentColor"
        d="M48.0226 13.2547L25.6601 0.311786C24.942 -0.103929 24.0559 -0.103929 23.3378 0.311786L0.976347 13.2547C0.372691 13.6041 0 14.2503 0 14.9502V41.0498C0 41.7496 0.372691 42.3958 0.976347 42.7453L23.3389 55.6882C24.057 56.1039 24.943 56.1039 25.6611 55.6882L48.0237 42.7453C48.6273 42.3958 49 41.7496 49 41.0498V14.9502C49 14.2503 48.6273 13.6041 48.0237 13.2547H48.0226ZM46.6179 15.9964L25.0302 53.4802C24.8842 53.7328 24.4989 53.6296 24.4989 53.337V28.793C24.4989 28.3026 24.2375 27.849 23.8134 27.6027L2.61094 15.3312C2.35898 15.1849 2.46186 14.7987 2.75372 14.7987H45.9292C46.5423 14.7987 46.9255 15.4649 46.619 15.9974L46.6179 15.9964Z"
      />
    </SvgIcon>
  );
}

const CLI_PRODUCT_IDS = new Set([
  'claude_code',
  'codex_cli',
  'gemini_cli',
  'copilot_cli',
  'opencode',
]);

const RUNTIME_PRODUCT_IDS = new Set(['ollama', 'llama_cpp']);

const EXTENSION_PRODUCT_IDS = new Set(['github_copilot', 'continue', 'cline', 'roo_code']);

/** Brand / category accent colors for inventory icons (currentColor). */
const PRODUCT_ICON_COLORS: Record<string, string> = {
  cursor: '#F54E00',
  vscode: '#007ACC',
  claude: '#D97757',
  claude_code: '#D97757',
  codex_cli: '#10A37F',
  gemini_cli: '#4285F4',
  copilot_cli: '#A371F7',
  github_copilot: '#238636',
  continue: '#1F6FEB',
  cline: '#D97757',
  roo_code: '#7C3AED',
  opencode: '#3B82F6',
  ollama: '#0D9373',
  llama_cpp: '#6366F1',
};

export function isCliAgent(productId: string, category?: string): boolean {
  const id = productId.trim().toLowerCase();
  if (CLI_PRODUCT_IDS.has(id)) return true;
  return (category || '').trim().toLowerCase() === 'cli_agent';
}

export function isLocalModelRuntime(productId: string, category?: string): boolean {
  const id = productId.trim().toLowerCase();
  if (RUNTIME_PRODUCT_IDS.has(id)) return true;
  return (category || '').trim().toLowerCase() === 'local_model_runtime';
}

export function isIdeExtension(productId: string, category?: string): boolean {
  const id = productId.trim().toLowerCase();
  if (EXTENSION_PRODUCT_IDS.has(id)) return true;
  const cat = (category || '').trim().toLowerCase();
  return cat === 'ai_ide_extension' || cat === 'agentic_ide_extension';
}

/** Accent color for an AI product icon; falls back by category. */
export function aiAppIconColor(productId: string, category?: string): string {
  const id = productId.trim().toLowerCase();
  if (PRODUCT_ICON_COLORS[id]) return PRODUCT_ICON_COLORS[id];
  if (isIdeExtension(id, category)) return '#7C3AED';
  if (isLocalModelRuntime(id, category)) return '#0D9373';
  if (isCliAgent(id, category)) return '#64748B';
  const cat = (category || '').trim().toLowerCase();
  if (cat === 'code_editor') return '#F54E00';
  if (cat === 'chat_client') return '#D97757';
  return '#7C3AED';
}

export function aiAppIcon(productId: string, props?: SvgIconProps, category?: string) {
  const id = productId.trim().toLowerCase();
  // No hardcoded gray — fill uses currentColor so parents can set brand color.
  const merged: SvgIconProps = { fontSize: 'small', ...props };
  if (id === 'cursor') {
    return <CursorIcon {...merged} />;
  }
  if (isIdeExtension(id, category)) {
    return <ExtensionIcon {...merged} />;
  }
  if (isLocalModelRuntime(id, category)) {
    return <MemoryIcon {...merged} />;
  }
  if (isCliAgent(id, category)) {
    return <TerminalIcon {...merged} />;
  }
  return <AutoAwesomeIcon {...merged} />;
}
