import { formatPinLabel } from './graphVisual';
import { NetworkMapNode } from '../types/networkMap';

describe('formatPinLabel', () => {
  it('formats flow summary as compact sessions label', () => {
    const node: NetworkMapNode = {
      id: 'flow_summary:443',
      type: 'flow_summary',
      label: '26 live sessions',
    };
    expect(formatPinLabel(node)).toBe('26 sessions');
  });

  it('formats port-based summary when present', () => {
    const node: NetworkMapNode = {
      id: 'flow_summary:443',
      type: 'flow_summary',
      label: '12 connections on 443',
    };
    expect(formatPinLabel(node)).toBe('12 sessions · :443');
  });

  it('formats port with colon prefix', () => {
    const node: NetworkMapNode = { id: 'port:443', type: 'port', label: '443' };
    expect(formatPinLabel(node)).toBe(':443');
  });

  it('formats flow IP label', () => {
    const node: NetworkMapNode = { id: 'flow:1', type: 'flow', label: '93.184.216.34' };
    expect(formatPinLabel(node)).toBe('93.184.216.34');
  });
});
