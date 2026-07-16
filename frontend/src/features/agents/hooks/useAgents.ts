import { useCallback, useEffect, useState } from 'react';
import { agentsApi } from '../config/api';
import { Agent } from '../types/agent';

export function useAgents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const registered = await agentsApi.list();
      setAgents(registered.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load agents');
      setAgents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { agents, loading, error, refresh };
}
