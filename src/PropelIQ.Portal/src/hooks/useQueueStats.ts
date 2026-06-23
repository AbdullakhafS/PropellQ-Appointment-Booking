import { useState, useEffect, useCallback, useRef } from 'react';
import { queueStatsApi } from '../api/queueStatsApi';
import type { QueueStats } from '../types/queueStats';

const POLL_INTERVAL_MS = 15_000; // Refresh every 15 s as a polling fallback

interface UseQueueStatsOptions {
  /** When true, stats refresh whenever this value changes (e.g. after queue events). */
  refreshTrigger?: number;
}

interface UseQueueStatsReturn {
  stats: QueueStats | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetches queue statistics and refreshes them on a timer.
 * Also re-fetches whenever `refreshTrigger` changes (e.g. after SSE events).
 */
export function useQueueStats({ refreshTrigger = 0 }: UseQueueStatsOptions = {}): UseQueueStatsReturn {
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await queueStatsApi.getStats();
      setStats(data);
    } catch {
      setError('Failed to load queue statistics.');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load + re-fetch on refreshTrigger change
  useEffect(() => { fetchStats(); }, [fetchStats, refreshTrigger]);

  // Polling fallback every 15 s
  useEffect(() => {
    timerRef.current = setInterval(fetchStats, POLL_INTERVAL_MS);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [fetchStats]);

  return { stats, loading, error, refresh: fetchStats };
}
