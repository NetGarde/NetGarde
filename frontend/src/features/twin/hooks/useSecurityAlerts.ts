import { useCallback, useEffect, useState } from 'react';
import { twinApi } from '../config/api';
import { SecurityAlert } from '../types/securityAlert';

export function useSecurityAlerts(options?: {
  pageSize?: number;
  severity?: string;
  alertType?: string;
  deviceId?: string;
}) {
  const pageSize = options?.pageSize ?? 50;
  const severity = options?.severity;
  const alertType = options?.alertType;
  const deviceId = options?.deviceId;
  const [items, setItems] = useState<SecurityAlert[]>([]);
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
        device_id: deviceId,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error('Failed to fetch security alerts:', error);
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [pageSize, severity, alertType, deviceId]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  return { items, total, loading, refetch: fetchAlerts };
}
