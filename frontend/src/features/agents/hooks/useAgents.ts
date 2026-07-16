import { useCallback, useEffect, useState } from 'react';
import { agentsApi } from '../config/api';
import { Agent } from '../types/agent';

export function useAgents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [connectedIds, setConnectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [registered, live] = await Promise.all([
        agentsApi.list(),
        agentsApi.listConnected(300).catch(() => ({ items: [], total: 0, connected_within_sec: 300 })),
      ]);
      setAgents(registered.items || []);
      const connected = new Set(
        (live.items || []).filter((a) => a.connected).map((a) => a.device_id),
      );
      setConnectedIds(connected);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load agents');
      setAgents([]);
      setConnectedIds(new Set());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { agents, connectedIds, loading, error, refresh };
}
