import { getAdminAuthHeaders } from '../../../shared/utils/authHeaders';
import { API_BASE_URL } from '../../../shared/config/apiBaseUrl';
import {
  TraverseRequest,
  TraverseResponse,
  TwinGraphSnapshot,
} from '../types/twinGraph';

export const DEFAULT_TWIN_GRAPH_MINUTES = 15;
export const DEFAULT_TWIN_GRAPH_POLL_SEC = 10;

export async function fetchTwinGraphSnapshot(
  minutes = DEFAULT_TWIN_GRAPH_MINUTES,
  includeFlows = false,
): Promise<TwinGraphSnapshot> {
  const params = new URLSearchParams({
    minutes: String(minutes),
    include_trusttwin: 'true',
  });
  if (includeFlows) {
    params.set('include_flows', 'true');
  }
  const res = await fetch(`${API_BASE_URL}/security/graph/snapshot?${params}`, {
    headers: {
      Accept: 'application/json',
      ...getAdminAuthHeaders(),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<TwinGraphSnapshot>;
}

export async function traverseTwinGraph(
  body: TraverseRequest,
  minutes = DEFAULT_TWIN_GRAPH_MINUTES,
  includeFlows = false,
): Promise<TraverseResponse> {
  const params = new URLSearchParams({
    minutes: String(minutes),
  });
  if (includeFlows) {
    params.set('include_flows', 'true');
  }
  const res = await fetch(`${API_BASE_URL}/security/graph/traverse?${params}`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...getAdminAuthHeaders(),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<TraverseResponse>;
}

export interface SimulationCommandRequest {
  prompt: string;
  active_ports?: number[];
  active_apps?: string[];
}

export interface SimulationCommandResponse {
  action:
    | 'block_port'
    | 'unblock_port'
    | 'block_gateway'
    | 'unblock_gateway'
    | 'clear_simulation'
    | 'enable_what_if'
    | 'noop'
    | 'unknown';
  port?: number | null;
  app_slug?: string | null;
  message: string;
  source: 'rules' | 'ollama';
}

export async function parseSimulationCommand(
  body: SimulationCommandRequest,
): Promise<SimulationCommandResponse> {
  const res = await fetch(`${API_BASE_URL}/security/simulate/command`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...getAdminAuthHeaders(),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<SimulationCommandResponse>;
}
