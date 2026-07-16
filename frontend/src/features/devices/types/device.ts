export interface Device {
  id: number;
  external_id: string;
  hostname: string | null;
  mac_address: string | null;
  source: string;
  last_seen_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}
