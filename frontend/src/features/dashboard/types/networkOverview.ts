export interface NetworkOverviewStats {
  reporting_clients: number;
  live_total_mib_per_sec: number;
  peak_mib_per_sec: number;
  alerts_total: number;
  enabled_policy_packs: number;
  /** @deprecated retained for older API payloads; omit or zero when unused */
  blocked_queries?: number;
  /** @deprecated retained for older API payloads; omit or zero when unused */
  elevated_behavior_clients?: number;
}

export type NetworkOverviewSource = 'template' | 'llm';

export interface NetworkOverview {
  generated_at: string;
  period_minutes: number;
  bullets: string[];
  summary?: string | null;
  stats: NetworkOverviewStats;
  source: NetworkOverviewSource;
  llm_model: string | null;
  review_mode: string;
  llm_error: string | null;
}
