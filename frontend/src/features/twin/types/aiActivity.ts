export type AiSessionCounters = {
  tool_executions: number;
  files_read: number;
  files_modified: number;
  network_connections: number;
  process_count: number;
};

export type AiSessionSummary = {
  session_id: string;
  device_id: string;
  app_name: string;
  root_process_id: string;
  root_pid: number;
  start_time: string;
  end_time?: string | null;
  duration_ms?: number | null;
  status: string;
  counters: AiSessionCounters;
  external_domains: string[];
  secrets_accessed: string[];
  git_repos: string[];
  docker_activity: string[];
  k8s_activity: string[];
  cloud_activity: string[];
  risk_score: number;
  risk_factors: string[];
  finding_count: number;
  process_count: number;
};

export type AiSessionListResponse = {
  device_id: string;
  total: number;
  items: AiSessionSummary[];
};

export type AiSessionDetail = AiSessionSummary & {
  processes: Record<string, unknown>;
  tools: Array<Record<string, unknown>>;
  findings: Array<Record<string, unknown>>;
  spawn_tree: Record<string, unknown>;
  activity_chain?: AiActivityChainStep[];
};

export type AiActivityChainStep = {
  kind: string;
  label: string;
  detail?: string;
  timestamp?: string;
  count?: number;
  artifacts?: Record<string, unknown>;
};

export type AiSessionChainResponse = {
  session_id: string;
  device_id: string;
  app_name: string;
  total: number;
  items: AiActivityChainStep[];
};

export type AiSessionGraphResponse = {
  session_id: string;
  device_id: string;
  app_name: string;
  graph: {
    nodes: Array<{ id: string; label: string; kind: string; role?: string; meta?: Record<string, unknown> }>;
    edges: Array<{ source: string; target: string; relation: string; meta?: Record<string, unknown> }>;
  };
};

export type AiSessionTimelineResponse = {
  session_id: string;
  device_id: string;
  total: number;
  items: Array<{
    kind: string;
    timestamp: string;
    process_id: string;
    summary: string;
    artifacts?: Record<string, unknown>;
  }>;
};
