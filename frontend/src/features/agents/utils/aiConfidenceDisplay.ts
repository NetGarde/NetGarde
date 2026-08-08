import type { AiSoftwareItem } from '../../twin/types/aiSoftware';

const EVIDENCE_LABEL: Record<string, string> = {
  candidate_name: 'App name',
  candidate_path: 'Install path',
  bundle_id: 'Bundle ID',
  signing_identifier: 'Code signing ID',
  team_id: 'Apple Team ID',
  signature_valid: 'Valid code signature',
  sha256: 'Binary hash',
};

export function evidenceLabel(key: string): string {
  return EVIDENCE_LABEL[key] || key.replace(/_/g, ' ');
}

export type ConfidenceExplanation = {
  level: string;
  summary: string;
  matched: string[];
  failed: string[];
  fromAgent: boolean;
};

/** Prefer agent-provided confidence_reason; fall back to local summary from evidence. */
export function explainConfidence(item: AiSoftwareItem): ConfidenceExplanation {
  const level = (item.confidence || 'UNKNOWN').toUpperCase();
  const matched = (item.matched_evidence || []).map(evidenceLabel);
  const failed = (item.failed_evidence || []).map(evidenceLabel);
  const agentReason = (item.confidence_reason || '').trim();
  if (agentReason) {
    return {
      level,
      summary: agentReason,
      matched,
      failed,
      fromAgent: true,
    };
  }
  return {
    level,
    summary: fallbackSummary(level, item.failed_evidence || []),
    matched,
    failed,
    fromAgent: false,
  };
}

function fallbackSummary(level: string, failed: string[]): string {
  switch (level) {
    case 'VERIFIED':
      return 'Strong identity match: bundle, signing, team, and signature all checked out.';
    case 'HIGH':
      return 'Strong match: bundle ID and code signature verified, with signing or team evidence.';
    case 'MEDIUM':
      return 'Partial cryptographic identity match. Some strong factors are missing.';
    case 'LOW':
      if (
        failed.includes('signature_valid') ||
        failed.includes('signing_identifier') ||
        failed.includes('team_id')
      ) {
        return 'Recognized mainly by name/path or bundle ID. Code-signing evidence is missing, so identity is not strongly verified.';
      }
      return 'Recognized mainly by name or install path. Strong identity checks did not pass.';
    case 'UNKNOWN':
      return 'Could not confidently identify this application.';
    default:
      return 'Identification confidence is based on catalog evidence (name, path, bundle, signing).';
  }
}

export function confidenceChipColor(
  level: string
): 'success' | 'info' | 'warning' | 'default' | 'error' {
  switch ((level || '').toUpperCase()) {
    case 'VERIFIED':
      return 'success';
    case 'HIGH':
      return 'info';
    case 'MEDIUM':
      return 'warning';
    case 'LOW':
      return 'default';
    default:
      return 'default';
  }
}
