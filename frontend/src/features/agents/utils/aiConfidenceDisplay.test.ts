import { explainConfidence, evidenceLabel } from './aiConfidenceDisplay';
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
});
