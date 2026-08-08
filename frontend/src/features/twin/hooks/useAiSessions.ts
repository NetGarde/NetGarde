import { useCallback, useEffect, useState } from 'react';
import { twinApi } from '../config/api';
import type {
  AiSessionChainResponse,
  AiSessionListResponse,
  AiSessionSummary,
} from '../types/aiActivity';

const EMPTY: AiSessionListResponse = { device_id: '', total: 0, items: [] };

export function useAiSessions(deviceId: string | undefined, limit = 50) {
  const [data, setData] = useState<AiSessionListResponse>(EMPTY);
  const [loading, setLoading] = useState(Boolean(deviceId));
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [chain, setChain] = useState<AiSessionChainResponse | null>(null);
  const [graph, setGraph] = useState<Awaited<ReturnType<typeof twinApi.getAiSessionGraph>> | null>(
    null
  );
  const [timeline, setTimeline] = useState<Awaited<
    ReturnType<typeof twinApi.getAiSessionTimeline>
  > | null>(null);

  const fetchSessions = useCallback(async () => {
    if (!deviceId) {
      setData(EMPTY);
      setLoading(false);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const payload = await twinApi.listAiSessions(deviceId, limit);
      setData(payload);
    } catch (err) {
      console.error('Failed to fetch AI sessions:', err);
      setData({ ...EMPTY, device_id: deviceId });
      setError(err instanceof Error ? err.message : 'Failed to load AI sessions');
    } finally {
      setLoading(false);
    }
  }, [deviceId, limit]);

  const selectSession = useCallback(async (sessionId: string | null) => {
    setSelectedId(sessionId);
    setChain(null);
    setGraph(null);
    setTimeline(null);
    if (!sessionId) return;
    setDetailLoading(true);
    try {
      const [c, g, t] = await Promise.all([
        twinApi.getAiSessionChain(sessionId),
        twinApi.getAiSessionGraph(sessionId),
        twinApi.getAiSessionTimeline(sessionId, 100),
      ]);
      setChain(c);
      setGraph(g);
      setTimeline(t);
    } catch (err) {
      console.error('Failed to fetch AI session detail:', err);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const selected: AiSessionSummary | undefined = data.items.find(
    (s) => s.session_id === selectedId
  );

  return {
    data,
    loading,
    error,
    refetch: fetchSessions,
    selectedId,
    selected,
    selectSession,
    detailLoading,
    chain,
    graph,
    timeline,
  };
}
