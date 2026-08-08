export type AiSoftwareItem = {
  id: string;
  product_id: string;
  product_name: string;
  vendor: string;
  category: string;
  confidence: string;
  confidence_reason?: string;
  installed: boolean;
  running: boolean;
  path: string;
  version: string;
  bundle_id: string;
  executable: string;
  signing_id: string;
  team_id: string;
  signature_valid?: boolean | null;
  matched_evidence?: string[];
  failed_evidence?: string[];
};

export type AiSoftwareListResponse = {
  device_id: string;
  total: number;
  items: AiSoftwareItem[];
};
