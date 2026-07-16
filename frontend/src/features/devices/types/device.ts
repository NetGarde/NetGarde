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

export interface QuarantineActionResult {
  device_id: number;
  in_quarantine: boolean;
  quarantine_expires_at: string | null;
  message: string;
}

export interface AppUsageSummaryItem {
  app_slug: string;
  app_display_name: string;
  total_active_seconds: number;
  total_active_hours: number;
  hourly_bucket_count: number;
  avg_active_minutes_per_hour: number;
}

export interface AppUsageSummaryResponse {
  device_id: number;
  hours: number;
  items: AppUsageSummaryItem[];
}

export interface AppUsageHourlyItem {
  window_start: string;
  hour_utc: number;
  app_slug: string;
  app_display_name: string;
  active_seconds: number;
  sample_count: number;
  active_minutes: number;
  usage_share_pct: number;
}

export interface AppUsageHourlyListResponse {
  device_id: number;
  hours: number;
  items: AppUsageHourlyItem[];
}

export interface DevicePolicyAssignment {
  device_id: number;
  policy_profile_id: number | null;
  policy_profile_slug: string | null;
  policy_profile_name: string | null;
  in_quarantine: boolean;
  quarantine_expires_at: string | null;
}
