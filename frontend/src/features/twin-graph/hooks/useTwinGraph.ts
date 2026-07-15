import { useCallback, useEffect, useState } from 'react';
import { devicesApi } from '../../devices/config/api';
import { NetworkMapResponse } from '../../network-map/types/networkMap';
import { projectAttributionGraph } from '../projections/projectGraph';
import {
  DEFAULT_TWIN_GRAPH_MINUTES,
  DEFAULT_TWIN_GRAPH_POLL_SEC,
  fetchTwinGraphSnapshot,
} from '../api/twinGraphApi';
import { TwinGraphSnapshot } from '../types/twinGraph';

export function useTwinGraph(
  minutes = DEFAULT_TWIN_GRAPH_MINUTES,
  pollSec = DEFAULT_TWIN_GRAPH_POLL_SEC,
  includeFlows = false,
) {
  const [snapshot, setSnapshot] = useState<TwinGraphSnapshot | null>(null);
  const [attribution, setAttribution] = useState<NetworkMapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDeviceIndex = useCallback(async () => {
    try {
      await devicesApi.list();
    } catch {
      // keep prior state
    }
  }, []);

  const load = useCallback(async () => {
    setError(null);
    try {
      await loadDeviceIndex();
      const response = await fetchTwinGraphSnapshot(minutes, includeFlows, true);
      setSnapshot(response);
      setAttribution(projectAttributionGraph(response));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load twin graph');
    } finally {
      setLoading(false);
    }
  }, [minutes, includeFlows, loadDeviceIndex]);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, pollSec * 1000);
    return () => window.clearInterval(timer);
  }, [load, pollSec]);

  return { snapshot, attribution, loading, error, liveConnected: false, reload: load };
}
