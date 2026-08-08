import { useCallback, useEffect, useState } from 'react';
import { agentsApi } from '../config/api';
import { twinApi } from '../../twin/config/api';
import { Agent } from '../types/agent';
import { AgentTelemetryEvent, ConnectedAgent } from '../../twin/types/connectedAgent';

export function useAgentDetail(agentId: string | undefined) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [live, setLive] = useState<ConnectedAgent | null>(null);
  const [events, setEvents] = useState<AgentTelemetryEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [liveMissing, setLiveMissing] = useState(false);

  const refresh = useCallback(async () => {
    if (!agentId) {
      setAgent(null);
      setLive(null);
      setEvents([]);
      setError('Missing agent id');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const registry = await agentsApi.get(agentId);
      setAgent(registry);

      const [liveResult, eventsResult] = await Promise.allSettled([
        twinApi.getConnectedAgent(agentId),
        twinApi.listDeviceEvents(agentId, 50),
      ]);

      if (liveResult.status === 'fulfilled') {
        setLive(liveResult.value);
        setLiveMissing(false);
      } else {
        setLive(null);
        setLiveMissing(true);
      }

      if (eventsResult.status === 'fulfilled') {
        setEvents(eventsResult.value.items || []);
      } else {
        setEvents([]);
      }
    } catch (e) {
      setAgent(null);
      setLive(null);
      setEvents([]);
      setError(e instanceof Error ? e.message : 'Failed to load agent');
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  const refreshEvents = useCallback(async () => {
    if (!agentId) {
      setEvents([]);
      return;
    }
    try {
      const eventsResult = await twinApi.listDeviceEvents(agentId, 50);
      setEvents(eventsResult.items || []);
    } catch {
      setEvents([]);
    }
  }, [agentId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { agent, live, events, loading, error, liveMissing, refresh, refreshEvents };
}
