import { getAdminAuthHeaders } from '../../../shared/utils/authHeaders';
import { API_BASE_URL } from '../../../shared/config/apiBaseUrl';
import { NetworkMapResponse } from '../types/networkMap';

export const DEFAULT_NETWORK_MAP_MINUTES = 15;
export const DEFAULT_NETWORK_MAP_POLL_SEC = 10;

export async function fetchNetworkAttributionMap(
  minutes = DEFAULT_NETWORK_MAP_MINUTES,
  _includeFlows = true,
): Promise<NetworkMapResponse> {
  const params = new URLSearchParams({ minutes: String(minutes) });
  const res = await fetch(`${API_BASE_URL}/network-flows/map?${params}`, {
    headers: {
      Accept: 'application/json',
      ...getAdminAuthHeaders(),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<NetworkMapResponse>;
}
