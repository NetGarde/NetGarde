import { getAdminAuthHeaders } from '../../../shared/utils/authHeaders';
import { API_BASE_URL } from '../../../shared/config/apiBaseUrl';
import { Agent, AgentListResponse } from '../types/agent';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...getAdminAuthHeaders(),
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const agentsApi = {
  list: () => apiFetch<AgentListResponse>('/agents'),
  get: (agentId: string) =>
    apiFetch<Agent>(`/agents/${encodeURIComponent(agentId)}`),
};
