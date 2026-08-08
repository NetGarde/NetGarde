import {
  explainConfidence,
  evidenceLabel,
  confidenceStrength,
  confidenceShortLabel,
  confidenceTone,
} from './aiConfidenceDisplay';
import type { AiSoftwareItem } from '../../twin/types/aiSoftware';

const base: AiSoftwareItem = {
  id: 'cursor:/applications/cursor.app',
  product_id: 'cursor',
  product_name: 'Cursor',
  vendor: 'Cursor',
  category: 'code_editor',
  confidence: 'LOW',
  installed: true,
  running: true,
  path: '/Applications/Cursor.app',
  version: '3.12.17',
  bundle_id: 'com.todesktop.230313mzl4w4u92',
  executable: 'Cursor',
  signing_id: '',
  team_id: '',
  matched_evidence: ['candidate_name', 'candidate_path', 'bundle_id'],
  failed_evidence: ['signing_identifier', 'team_id', 'signature_valid'],
};

describe('aiConfidenceDisplay', () => {
  it('labels evidence keys', () => {
    expect(evidenceLabel('signature_valid')).toBe('Valid code signature');
  });

  it('prefers agent confidence_reason', () => {
    const expl = explainConfidence({
      ...base,
      confidence_reason:
        'LOW. Recognized mainly by name/path or bundle ID; code-signing evidence is missing; matched: app name, install path, bundle ID; missing: code signing ID, Apple Team ID, valid code signature.',
    });
    expect(expl.fromAgent).toBe(true);
    expect(expl.summary).toMatch(/^LOW\./);
    expect(expl.summary).toMatch(/code-signing/i);
  });

  it('falls back when agent reason is absent', () => {
    const expl = explainConfidence(base);
    expect(expl.fromAgent).toBe(false);
    expect(expl.summary).toMatch(/code-signing/i);
    expect(expl.matched).toContain('Bundle ID');
    expect(expl.failed).toContain('Valid code signature');
  });

  it('labels CLI evidence keys', () => {
    expect(evidenceLabel('package_identity')).toBe('Package identity');
    expect(evidenceLabel('command')).toBe('Command name');
  });

  it('labels local model runtime evidence keys', () => {
    expect(evidenceLabel('listener')).toBe('Network listener');
    expect(evidenceLabel('runtime_fingerprint')).toBe('Runtime fingerprint');
    expect(evidenceLabel('local_client')).toBe('Local client');
  });

  it('labels IDE extension evidence keys', () => {
    expect(evidenceLabel('extension_id')).toBe('Extension ID');
    expect(evidenceLabel('host_ide')).toBe('Host IDE');
    expect(evidenceLabel('mcp_configured')).toBe('MCP configured');
  });

  it('maps confidence to meter strength and tone', () => {
    expect(confidenceStrength('VERIFIED')).toBe(4);
    expect(confidenceStrength('HIGH')).toBe(3);
    expect(confidenceStrength('MEDIUM')).toBe(2);
    expect(confidenceStrength('LOW')).toBe(1);
    expect(confidenceShortLabel('HIGH')).toBe('High');
    expect(confidenceTone('HIGH')).toBe('success.main');
    expect(confidenceTone('LOW')).toBe('error.main');
  });
});
