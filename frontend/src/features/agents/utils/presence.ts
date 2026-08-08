/** Agents seen within this window are shown as online. */
export const AGENT_ONLINE_WITHIN_SEC = 300;

export function isAgentOnline(lastSeenAt: string | null | undefined, nowMs = Date.now()): boolean {
  if (!lastSeenAt) return false;
  const ts = Date.parse(lastSeenAt);
  if (Number.isNaN(ts)) return false;
  return nowMs - ts <= AGENT_ONLINE_WITHIN_SEC * 1000;
}
