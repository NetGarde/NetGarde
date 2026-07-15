import { useCallback, useEffect, useState } from 'react';
import { devicesApi } from '../../devices/config/api';
import {
  DEFAULT_NETWORK_MAP_MINUTES,
  DEFAULT_NETWORK_MAP_POLL_SEC,
  fetchNetworkAttributionMap,
} from '../config/api';
import { NetworkMapResponse } from '../types/networkMap';

export function useNetworkAttributionMap(
  minutes = DEFAULT_NETWORK_MAP_MINUTES,
  pollSec = DEFAULT_NETWORK_MAP_POLL_SEC,
  includeFlows = false,
) {
  const [data, setData] = useState<NetworkMapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDeviceIndex = useCallback(async () => {
    try {
      await devicesApi.list();
    } catch {
      // keep prior state if refresh fails
    }
  }, []);

  const load = useCallback(async () => {
    setError(null);
    try {
      await loadDeviceIndex();
      const response = await fetchNetworkAttributionMap(minutes, includeFlows);
      setData(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load network map');
    } finally {
      setLoading(false);
    }
  }, [minutes, loadDeviceIndex, includeFlows]);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, pollSec * 1000);
    return () => window.clearInterval(timer);
  }, [load, pollSec]);

  return { data, loading, error, liveConnected: false, reload: load };
}
