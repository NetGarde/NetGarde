import {
  displayBaselineKey,
  isBaselineNoise,
  prepareBaselineItems,
  sortBaselineItems,
} from './baselineDisplay';
import { DeviceBaselineItem } from '../../twin/types/deviceBaseline';

function item(key: string, count = 1, kind = 'process_comm'): DeviceBaselineItem {
  return {
    behavior_kind: kind,
    behavior_key: key,
    count,
    first_seen_at: '2026-08-03T12:00:00Z',
    last_seen_at: '2026-08-03T12:00:00Z',
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

  it('sorts by count descending then name', () => {
    const sorted = sortBaselineItems([item('zsh', 1), item('google', 5), item('docker', 5)]);
    expect(sorted.map((i) => i.behavior_key)).toEqual(['docker', 'google', 'zsh']);
  });

  it('prepareBaselineItems filters by default and can include system', () => {
    const items = [item('google'), item('(ps)'), item('contactsd'), item('zsh', 3)];
    const apps = prepareBaselineItems(items, { includeSystem: false });
    expect(apps.map((i) => i.behavior_key)).toEqual(['zsh', 'google']);
    const all = prepareBaselineItems(items, { includeSystem: true });
    expect(all).toHaveLength(4);
  });

  it('displayBaselineKey renames known apps', () => {
    expect(displayBaselineKey('google')).toBe('Chrome');
    expect(displayBaselineKey('zsh')).toBe('Terminal (zsh)');
  });
});
