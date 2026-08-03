export type DeviceBaselineItem = {
  behavior_kind: string;
  behavior_key: string;
  count: number;
  first_seen_at: string;
  last_seen_at: string;
  established: boolean;
};

export type DeviceBaselineResponse = {
  device_id: string;
  profile_warm: boolean;
  total: number;
  items: DeviceBaselineItem[];
  suppress_count: number;
  suppress_age_hours: number;
  profile_min_keys: number;
};
