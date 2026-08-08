export interface Agent {
  id: number;
  agent_id: string;
  hostname: string | null;
  os: string | null;
  os_version: string | null;
  arch: string | null;
  agent_version: string | null;
  status: string;
  first_seen_at: string;
  last_seen_at: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AgentListResponse {
  items: Agent[];
  total: number;
}
