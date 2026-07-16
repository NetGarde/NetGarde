import { AGENT_ONLINE_WITHIN_SEC, isAgentOnline } from '../utils/presence';

describe('isAgentOnline', () => {
  const now = Date.parse('2026-07-16T12:00:00.000Z');

  it('is online when last seen within the window', () => {
    const recent = new Date(now - (AGENT_ONLINE_WITHIN_SEC - 10) * 1000).toISOString();
    expect(isAgentOnline(recent, now)).toBe(true);
  });

  it('is offline when last seen outside the window', () => {
    const stale = new Date(now - (AGENT_ONLINE_WITHIN_SEC + 10) * 1000).toISOString();
    expect(isAgentOnline(stale, now)).toBe(false);
  });

  it('is offline when last seen is missing', () => {
    expect(isAgentOnline(null, now)).toBe(false);
    expect(isAgentOnline(undefined, now)).toBe(false);
    expect(isAgentOnline('', now)).toBe(false);
  });
});
