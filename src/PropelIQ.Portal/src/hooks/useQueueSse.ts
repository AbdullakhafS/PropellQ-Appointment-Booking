import { useState, useEffect, useRef, useCallback } from 'react';
import type { QueueAppointment } from '../types/queue';
import type { QueueEventPayload, SseConnectionStatus } from '../types/queueEvents';
import { eventToQueueAppointment } from '../types/queueEvents';

const SSE_URL = '/api/queue/events';
const RECONNECT_DELAY_MS = 3000;

interface QueueReorderPayload {
  orderedIds: string[];
  newVersion: number;
  occurredAt: string;
}

interface UseQueueSseReturn {
  items: QueueAppointment[];
  connectionStatus: SseConnectionStatus;
  queueVersion: number;
  setInitialItems: (items: QueueAppointment[], version?: number) => void;
}

export function useQueueSse(): UseQueueSseReturn {
  const [items, setItems] = useState<QueueAppointment[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<SseConnectionStatus>('connecting');
  const [queueVersion, setQueueVersion] = useState(0);
  const esRef = useRef<EventSource | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const setInitialItems = useCallback((snapshot: QueueAppointment[], version = 0) => {
    setItems(snapshot);
    setQueueVersion(version);
  }, []);

  const connect = useCallback(() => {
    if (esRef.current) esRef.current.close();

    setConnectionStatus('connecting');
    const es = new EventSource(SSE_URL);
    esRef.current = es;

    es.onopen = () => setConnectionStatus('connected');

    const handleQueueEvent = (e: MessageEvent) => {
      try {
        const payload: QueueEventPayload = JSON.parse(e.data);

        setItems(prev => {
          switch (payload.eventType) {
            case 'Added':
              if (prev.some(a => a.appointmentId === payload.appointmentId)) return prev;
              return [...prev, eventToQueueAppointment(payload)].sort(
                (a, b) => a.position - b.position || new Date(a.appointmentTime).getTime() - new Date(b.appointmentTime).getTime()
              );

            case 'Updated':
              return prev.map(a =>
                a.appointmentId === payload.appointmentId
                  ? eventToQueueAppointment(payload)
                  : a
              );

            case 'Removed':
              return prev.filter(a => a.appointmentId !== payload.appointmentId);

            default:
              return prev;
          }
        });
      } catch { /* skip malformed event */ }
    };

    // Handle queue.reordered — reorder items list to match server order
    es.addEventListener('queue.reordered', (e: MessageEvent) => {
      try {
        const payload: QueueReorderPayload = JSON.parse(e.data);
        setQueueVersion(payload.newVersion);
        setItems(prev => {
          const indexMap = new Map(payload.orderedIds.map((id, i) => [id, i]));
          return [...prev].sort((a, b) =>
            (indexMap.get(a.appointmentId) ?? 999) - (indexMap.get(b.appointmentId) ?? 999)
          );
        });
      } catch { /* skip */ }
    });

    es.addEventListener('queue.added', handleQueueEvent);
    es.addEventListener('queue.updated', handleQueueEvent);
    es.addEventListener('queue.removed', handleQueueEvent);

    es.onerror = () => {
      setConnectionStatus('reconnecting');
      es.close();
      esRef.current = null;
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      esRef.current?.close();
    };
  }, [connect]);

  return { items, connectionStatus, queueVersion, setInitialItems };
}
