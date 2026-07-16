import { useCallback, useEffect, useState } from 'react';
import { twinApi } from '../config/api';
import { TwinAlert } from '../types/twinAlert';

export function useTwinAlerts(options?: {
  pageSize?: number;
  severity?: string;
  alertType?: string;
}) {
  const pageSize = options?.pageSize ?? 50;
  const severity = options?.severity;
  const alertType = options?.alertType;
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
        alert_type: alertType,
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
  }, [pageSize, severity, alertType]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  return { items, total, loading, refetch: fetchAlerts };
}
