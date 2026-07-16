import { getAdminAuthHeaders } from '../../../shared/utils/authHeaders';
import { API_BASE_URL } from '../../../shared/config/apiBaseUrl';
import { SecurityAlertListParams, SecurityAlertListResponse } from '../types/securityAlert';
import { ConnectedAgentListResponse } from '../types/connectedAgent';

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

function listAlertsQuery(params: SecurityAlertListParams = {}): string {
  const search = new URLSearchParams();
  if (params.page != null) search.set('page', String(params.page));
  if (params.page_size != null) search.set('page_size', String(params.page_size));
  if (params.severity) search.set('severity', params.severity);
  if (params.alert_type) search.set('alert_type', params.alert_type);
  if (params.device_id) search.set('device_id', params.device_id);
  const qs = search.toString();
  return qs ? `/security/alerts?${qs}` : '/security/alerts';
}

export const twinApi = {
  listAlerts: (params?: SecurityAlertListParams) =>
    apiFetch<SecurityAlertListResponse>(listAlertsQuery(params)),
  listConnectedAgents: (connectedWithinSec = 300) =>
    apiFetch<ConnectedAgentListResponse>(
      `/security/agents?connected_within_sec=${encodeURIComponent(String(connectedWithinSec))}`
    ),
};
