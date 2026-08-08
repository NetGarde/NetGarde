import type { AiSoftwareItem } from '../../twin/types/aiSoftware';

const EVIDENCE_LABEL: Record<string, string> = {
  candidate_name: 'App name',
  candidate_path: 'Install path',
  bundle_id: 'Bundle ID',
  signing_identifier: 'Code signing ID',
  team_id: 'Apple Team ID',
  signature_valid: 'Valid code signature',
  sha256: 'Binary hash',
  command: 'Command name',
  package_manager: 'Package manager',
  package_identity: 'Package identity',
  package_provenance: 'Package provenance',
  entry_point: 'Entry point',
  invocation_path: 'Invocation path',
  docker_image: 'Docker image',
  listener: 'Network listener',
  listener_exposure: 'Listener exposure',
  runtime_fingerprint: 'Runtime fingerprint',
  model_artifact: 'Model artifact',
  local_client: 'Local client',
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
    case 'HIGH':
      return 'success';
    case 'MEDIUM':
      return 'warning';
    case 'LOW':
      return 'error';
    default:
      return 'default';
  }
}

/** Filled segments out of 4 for a compact strength meter. */
export function confidenceStrength(level: string): number {
  switch ((level || '').toUpperCase()) {
    case 'VERIFIED':
      return 4;
    case 'HIGH':
      return 3;
    case 'MEDIUM':
      return 2;
    case 'LOW':
      return 1;
    default:
      return 0;
  }
}

/** Theme palette key for confidence accent (text + meter). */
export function confidenceTone(
  level: string
): 'success.main' | 'warning.main' | 'error.main' | 'text.disabled' {
  switch ((level || '').toUpperCase()) {
    case 'VERIFIED':
    case 'HIGH':
      return 'success.main';
    case 'MEDIUM':
      return 'warning.main';
    case 'LOW':
      return 'error.main';
    default:
      return 'text.disabled';
  }
}

export function confidenceShortLabel(level: string): string {
  switch ((level || '').toUpperCase()) {
    case 'VERIFIED':
      return 'Verified';
    case 'HIGH':
      return 'High';
    case 'MEDIUM':
      return 'Medium';
    case 'LOW':
      return 'Low';
    default:
      return 'Unknown';
  }
}
