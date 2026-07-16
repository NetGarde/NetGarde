import { getAdminAuthHeaders } from '../../../shared/utils/authHeaders';
import {
  Device,
  DevicePolicyAssignment,
  QuarantineActionResult,
  AppUsageSummaryResponse,
  AppUsageHourlyListResponse,
} from '../types/device';

import { API_BASE_URL } from '../../../shared/config/apiBaseUrl';

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

export const devicesApi = {
  list: () => apiFetch<Device[]>('/devices'),
  getPolicyAssignment: (deviceId: number) =>
    apiFetch<DevicePolicyAssignment>(`/devices/${deviceId}/policy-assignment`),
  assignPolicyProfile: (deviceId: number, policy_profile_slug: string) =>
    apiFetch<DevicePolicyAssignment>(`/devices/${deviceId}/policy-assignment`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ policy_profile_slug }),
    }),
  startQuarantine: (deviceId: number, hours = 4) =>
    apiFetch<QuarantineActionResult>(`/devices/${deviceId}/quarantine`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hours }),
    }),
  endQuarantine: (deviceId: number) =>
    apiFetch<QuarantineActionResult>(`/devices/${deviceId}/quarantine`, {
      method: 'DELETE',
    }),
  getNetworkAttributionSummary: (deviceId: number, hours = 168) =>
    apiFetch<AppUsageSummaryResponse>(
      `/devices/${deviceId}/network-attribution/summary?hours=${hours}`,
    ),
  getNetworkAttributionHourly: (deviceId: number, hours = 168, appSlug?: string) => {
    const params = new URLSearchParams({ hours: String(hours) });
    if (appSlug) {
      params.set('app_slug', appSlug);
    }
    return apiFetch<AppUsageHourlyListResponse>(
      `/devices/${deviceId}/network-attribution?${params.toString()}`,
    );
  },
};
