import { useCallback, useEffect, useState } from 'react';
import { twinApi } from '../config/api';
import { AiSoftwareListResponse } from '../types/aiSoftware';

const EMPTY: AiSoftwareListResponse = {
  device_id: '',
  total: 0,
  items: [],
};

export function useAiSoftware(deviceId: string | undefined) {
  const [data, setData] = useState<AiSoftwareListResponse>(EMPTY);
  const [loading, setLoading] = useState(Boolean(deviceId));
  const [error, setError] = useState<string | null>(null);

  const fetchSoftware = useCallback(async () => {
    if (!deviceId) {
      setData(EMPTY);
      setLoading(false);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const payload = await twinApi.listAiSoftware(deviceId);
      setData(payload);
    } catch (err) {
      console.error('Failed to fetch AI tools inventory:', err);
      setData({ ...EMPTY, device_id: deviceId });
      setError(err instanceof Error ? err.message : 'Failed to load AI tools inventory');
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  useEffect(() => {
    fetchSoftware();
  }, [fetchSoftware]);

  return { data, loading, error, refetch: fetchSoftware };
}
