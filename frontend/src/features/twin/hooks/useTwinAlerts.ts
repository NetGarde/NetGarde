import { useCallback, useEffect, useState } from 'react';
import { twinApi } from '../config/api';
import { TwinAlert } from '../types/twinAlert';

export function useTwinAlerts(options?: { pageSize?: number; severity?: string }) {
  const pageSize = options?.pageSize ?? 20;
  const severity = options?.severity ?? 'high';
  const [items, setItems] = useState<TwinAlert[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await twinApi.listAlerts({
        page: 1,
        page_size: pageSize,
        severity,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error('Failed to fetch attack alerts:', error);
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [pageSize, severity]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  return { items, total, loading, refetch: fetchAlerts };
}
