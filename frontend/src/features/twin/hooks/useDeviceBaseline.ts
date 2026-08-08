import { useCallback, useEffect, useState } from 'react';
import { twinApi } from '../config/api';
import { DeviceBaselineResponse } from '../types/deviceBaseline';

const EMPTY: DeviceBaselineResponse = {
  device_id: '',
  profile_warm: false,
  total: 0,
  items: [],
  suppress_count: 20,
  suppress_age_hours: 0,
  profile_min_keys: 5,
};

export function useDeviceBaseline(deviceId: string | undefined, limit = 100) {
  const [data, setData] = useState<DeviceBaselineResponse>(EMPTY);
  const [loading, setLoading] = useState(Boolean(deviceId));
  const [flushing, setFlushing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBaseline = useCallback(async () => {
    if (!deviceId) {
      setData(EMPTY);
      setLoading(false);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const payload = await twinApi.getDeviceBaseline(deviceId, limit);
      setData(payload);
    } catch (err) {
      console.error('Failed to fetch device baseline:', err);
      setData({ ...EMPTY, device_id: deviceId });
      setError(err instanceof Error ? err.message : 'Failed to load baseline');
    } finally {
      setLoading(false);
    }
  }, [deviceId, limit]);

  const flushBaseline = useCallback(async () => {
    if (!deviceId) return;
    setFlushing(true);
    setError(null);
    try {
      await twinApi.clearDeviceBaseline(deviceId);
      await fetchBaseline();
    } catch (err) {
      console.error('Failed to flush device baseline:', err);
      setError(err instanceof Error ? err.message : 'Failed to flush baseline');
    } finally {
      setFlushing(false);
    }
  }, [deviceId, fetchBaseline]);

  useEffect(() => {
    fetchBaseline();
  }, [fetchBaseline]);

  return { data, loading, flushing, error, refetch: fetchBaseline, flush: flushBaseline };
}
