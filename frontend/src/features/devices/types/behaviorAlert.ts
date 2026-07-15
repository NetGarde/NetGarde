export interface BehaviorAlert {
  id: number;
  timestamp: string;
  client_ip: string;
  device_id?: number | null;
  alert_type: string;
  severity: string;
  domain: string | null;
  root_domain: string | null;
  message: string | null;
  parent_summary?: string | null;
  created_at: string | null;
}

export interface BehaviorAlertListResponse {
  items: BehaviorAlert[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
