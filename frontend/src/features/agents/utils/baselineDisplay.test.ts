import {
  displayBaselineKey,
  isBaselineNoise,
  prepareBaselineItems,
  sortBaselineItems,
} from './baselineDisplay';
import { DeviceBaselineItem } from '../../twin/types/deviceBaseline';

function item(
  key: string,
  count = 1,
  kind = 'process_comm',
  lastSeen = '2026-08-03T12:00:00Z'
): DeviceBaselineItem {
  return {
    behavior_kind: kind,
    behavior_key: key,
    count,
    first_seen_at: '2026-08-03T10:00:00Z',
    last_seen_at: lastSeen,
    established: false,
  };
}

describe('baselineDisplay', () => {
  it('marks parenthesized and daemon names as noise', () => {
    expect(isBaselineNoise(item('(ps)'))).toBe(true);
    expect(isBaselineNoise(item('ps'))).toBe(true);
    expect(isBaselineNoise(item('contactsd'))).toBe(true);
    expect(isBaselineNoise(item('taskgated-helper'))).toBe(true);
    expect(isBaselineNoise(item('mdworker_shared'))).toBe(true);
  });

  it('keeps application-like process names', () => {
    expect(isBaselineNoise(item('google'))).toBe(false);
    expect(isBaselineNoise(item('zsh'))).toBe(false);
    expect(isBaselineNoise(item('docker'))).toBe(false);
    expect(isBaselineNoise(item('Cursor'))).toBe(false);
    expect(isBaselineNoise(item('/tmp/evil', 1, 'temp_path'))).toBe(false);
  });

  it('sorts by last_seen descending then count', () => {
    const sorted = sortBaselineItems([
      item('zsh', 9, 'process_comm', '2026-08-03T12:00:00Z'),
      item('google', 1, 'process_comm', '2026-08-03T14:00:00Z'),
      item('docker', 5, 'process_comm', '2026-08-03T13:00:00Z'),
    ]);
    expect(sorted.map((i) => i.behavior_key)).toEqual(['google', 'docker', 'zsh']);
  });

  it('prepareBaselineItems filters by default and can include system', () => {
    const items = [
      item('google', 1, 'process_comm', '2026-08-03T14:00:00Z'),
      item('(ps)'),
      item('contactsd'),
      item('zsh', 3, 'process_comm', '2026-08-03T13:00:00Z'),
    ];
    const apps = prepareBaselineItems(items, { includeSystem: false });
    expect(apps.map((i) => i.behavior_key)).toEqual(['google', 'zsh']);
    const all = prepareBaselineItems(items, { includeSystem: true });
    expect(all).toHaveLength(4);
  });

  it('prepareBaselineItems supports search query', () => {
    const items = [item('google'), item('zsh'), item('docker'), item('mail')];
    const chrome = prepareBaselineItems(items, { includeSystem: true, query: 'chrome' });
    expect(chrome.map((i) => i.behavior_key)).toEqual(['google']);
    const mail = prepareBaselineItems(items, { includeSystem: true, query: 'mai' });
    expect(mail.map((i) => i.behavior_key)).toEqual(['mail']);
  });

  it('displayBaselineKey renames known apps', () => {
    expect(displayBaselineKey('google')).toBe('Chrome');
    expect(displayBaselineKey('zsh')).toBe('Terminal (zsh)');
    expect(displayBaselineKey('mail')).toBe('Mail');
  });
});
