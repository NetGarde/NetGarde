import {
  appDisplayName,
  formatDurationMs,
  riskTone,
  sessionSubtitle,
  extractSessionIdFromDetail,
} from './aiSessionDisplay';

describe('aiSessionDisplay', () => {
  it('formats duration', () => {
    expect(formatDurationMs(5000)).toBe('5s');
    expect(formatDurationMs(125000)).toBe('2m 5s');
  });

  it('maps app names', () => {
    expect(appDisplayName('cursor')).toBe('Cursor');
    expect(appDisplayName('vscode')).toBe('VS Code');
  });

  it('risk tones', () => {
    expect(riskTone(80)).toBe('error');
    expect(riskTone(50)).toBe('warning');
    expect(riskTone(10)).toBe('info');
  });

  it('session subtitle', () => {
    const text = sessionSubtitle({
      session_id: 'ais_1',
      device_id: 'd',
      app_name: 'cursor',
      root_process_id: 'p',
      root_pid: 1,
      start_time: '',
      status: 'active',
      counters: {
        tool_executions: 3,
        files_read: 0,
        files_modified: 0,
        network_connections: 2,
        process_count: 5,
      },
      external_domains: [],
      secrets_accessed: [],
      git_repos: [],
      docker_activity: [],
      k8s_activity: [],
      cloud_activity: [],
      risk_score: 50,
      risk_factors: [],
      finding_count: 1,
      process_count: 5,
    });
    expect(text).toContain('3 tools');
    expect(text).toContain('1 findings');
  });

  it('extracts session_id from detail json', () => {
    expect(extractSessionIdFromDetail('{"session_id":"ais_abc"}')).toBe('ais_abc');
    expect(extractSessionIdFromDetail('not-json')).toBeNull();
  });
});
