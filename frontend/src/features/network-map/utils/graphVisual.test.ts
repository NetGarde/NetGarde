import { formatPinLabel } from './graphVisual';
import { NetworkMapNode } from '../types/networkMap';

describe('formatPinLabel', () => {
  it('formats flow summary as compact sessions label', () => {
    const node: NetworkMapNode = {
      id: 'flow_summary:443',
      type: 'flow_summary',
      label: '26 connections on 443',
    };
    expect(formatPinLabel(node, true)).toBe('26 sessions · :443');
  });

  it('formats port with colon prefix', () => {
    const node: NetworkMapNode = { id: 'port:443', type: 'port', label: '443' };
    expect(formatPinLabel(node, true)).toBe(':443');
  });
});
