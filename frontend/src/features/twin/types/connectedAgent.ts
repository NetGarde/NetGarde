export type ConnectedAgent = {
  device_id: string;
  hostname?: string | null;
  os?: string | null;
  os_version?: string | null;
  arch?: string | null;
  agent_version?: string | null;
  status?: string | null;
  public_ip?: string | null;
  network_type?: string | null;
  listening_count?: number | null;
  established_count?: number | null;
  presence?: string | null;
  idle_sec?: number | null;
  app_switches?: number | null;
  last_seen_at?: string | null;
  connected: boolean;
  client_details?: Record<string, unknown>;
  network_summary?: Record<string, unknown>;
  action_summary?: Record<string, unknown>;
};

export type ConnectedAgentListResponse = {
  items: ConnectedAgent[];
  total: number;
  connected_within_sec: number;
};

export type AgentTelemetryEvent = {
  event_id: string;
  device_id: string;
  type: string;
  ts?: string | null;
  payload: Record<string, unknown>;
};

export type AgentTelemetryEventListResponse = {
  items: AgentTelemetryEvent[];
  total: number;
  device_id: string;
};

