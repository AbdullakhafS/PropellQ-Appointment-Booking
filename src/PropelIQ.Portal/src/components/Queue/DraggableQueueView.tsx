import React, { useState, useRef, useCallback, useEffect } from 'react';
import { queueApi } from '../../api/queueApi';
import { useQueueSse } from '../../hooks/useQueueSse';
import { WalkInBadge } from '../WalkIn/WalkInBadge';
import type { QueueAppointment } from '../../types/queue';
import styles from './DraggableQueueView.module.css';

// ----- helpers -----

function reorder<T>(list: T[], from: number, to: number): T[] {
  if (from === to) return list;
  const result = [...list];
  const [moved] = result.splice(from, 1);
  result.splice(to, 0, moved);
  return result;
}

const STATUS_LABELS: Record<string, string> = {
  scheduled: 'Scheduled',
  arrived: 'Arrived',
  completed: 'Completed',
  cancelled: 'Cancelled',
};

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === 'arrived' ? styles.arrived :
    status === 'completed' ? styles.completed :
    status === 'cancelled' ? styles.cancelled :
    styles.scheduled;
  return <span className={`${styles.statusBadge} ${cls}`}>{STATUS_LABELS[status] ?? status}</span>;
}

interface DraggableQueueViewProps {
  date?: string;
}

export function DraggableQueueView({ date }: DraggableQueueViewProps) {
  const { items: liveItems, connectionStatus, queueVersion, setInitialItems } = useQueueSse();
  const [localItems, setLocalItems] = useState<QueueAppointment[]>([]);
  const [dragFromIdx, setDragFromIdx] = useState<number | null>(null);
  const [dragOverIdx, setDragOverIdx] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [conflictError, setConflictError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const versionRef = useRef(0);

  // Sync SSE live items → local (only when not mid-drag)
  useEffect(() => {
    if (dragFromIdx === null) setLocalItems(liveItems);
  }, [liveItems, dragFromIdx]);

  // Load initial snapshot
  const loadSnapshot = useCallback(async () => {
    try {
      const result = await queueApi.getQueue({ date });
      setInitialItems(result.items, result.version);
      versionRef.current = result.version;
      setLocalItems(result.items);
    } catch { /* non-fatal */ }
  }, [date, setInitialItems]);

  useEffect(() => { loadSnapshot(); }, [loadSnapshot]);

  // Keep version ref in sync
  useEffect(() => { versionRef.current = queueVersion; }, [queueVersion]);

  // ----- HTML5 Drag API handlers -----

  const handleDragStart = (idx: number) => setDragFromIdx(idx);
  const handleDragEnd = () => { setDragFromIdx(null); setDragOverIdx(null); };

  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    setDragOverIdx(idx);
    if (dragFromIdx !== null && dragFromIdx !== idx) {
      setLocalItems(prev => reorder(prev, dragFromIdx, idx));
      setDragFromIdx(idx);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragFromIdx(null);
    setDragOverIdx(null);
    await saveReorder();
  };

  // ----- Keyboard fallback: Move Up / Move Down buttons -----

  const moveItem = async (idx: number, direction: -1 | 1) => {
    const target = idx + direction;
    if (target < 0 || target >= localItems.length) return;
    setLocalItems(prev => reorder(prev, idx, target));
    await saveReorder(reorder(localItems, idx, target));
  };

  // ----- Persist reorder -----

  const saveReorder = useCallback(async (orderedItems?: QueueAppointment[]) => {
    const items = orderedItems ?? localItems;
    setSaving(true);
    setSaveError(null);
    setConflictError(null);

    try {
      await queueApi.reorder({
        orderedAppointmentIds: items.map(a => a.appointmentId),
        expectedVersion: versionRef.current,
      });
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        setConflictError(
          'Another user changed the queue order at the same time. The queue has been refreshed.'
        );
        await loadSnapshot();
      } else {
        setSaveError('Failed to save queue order. Please try again.');
      }
    } finally {
      setSaving(false);
    }
  }, [localItems, loadSnapshot]);

  const connLabel =
    connectionStatus === 'connected' ? 'Live' :
    connectionStatus === 'reconnecting' ? 'Reconnecting…' : 'Connecting…';

  const connCls =
    connectionStatus === 'connected' ? styles.connGreen :
    connectionStatus === 'reconnecting' ? styles.connAmber :
    styles.connGrey;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h2 className={styles.title}>Queue</h2>
          <span className={`${styles.connBadge} ${connCls}`} aria-live="polite">
            <span className={styles.connDot} aria-hidden="true" />
            {connLabel}
          </span>
          {saving && <span className={styles.savingIndicator} aria-live="polite">Saving…</span>}
        </div>
        <p className={styles.hint}>Drag rows to reorder. Use ↑↓ buttons for keyboard access.</p>
      </header>

      {conflictError && (
        <div className={styles.conflictBanner} role="alert">
          ⚠ {conflictError}
          <button type="button" className={styles.refreshBtn} onClick={loadSnapshot}>
            Refresh
          </button>
        </div>
      )}

      {saveError && (
        <div className={styles.errorBanner} role="alert">
          {saveError}
          <button type="button" className={styles.retryBtn} onClick={() => saveReorder()}>
            Retry
          </button>
        </div>
      )}

      {localItems.length === 0 ? (
        <div className={styles.empty} role="status">
          <p>No appointments in queue.</p>
        </div>
      ) : (
        <ol className={styles.list} aria-label="Reorderable appointment queue" role="listbox">
          {localItems.map((appt, idx) => {
            const isDragging = dragFromIdx === idx;
            const isOver = dragOverIdx === idx;

            return (
              <li
                key={appt.appointmentId}
                className={`${styles.row} ${isDragging ? styles.dragging : ''} ${isOver ? styles.dragOver : ''} ${appt.isWalkIn ? styles.walkIn : ''}`}
                draggable
                onDragStart={() => handleDragStart(idx)}
                onDragEnd={handleDragEnd}
                onDragOver={e => handleDragOver(e, idx)}
                onDrop={handleDrop}
                aria-selected={isDragging}
                role="option"
                tabIndex={0}
                aria-label={`Position ${idx + 1}: ${appt.patientFullName}, ${appt.providerName}`}
              >
                {/* Drag handle */}
                <span className={styles.handle} aria-hidden="true">⠿</span>

                {/* Content */}
                <div className={styles.rowContent}>
                  <span className={styles.pos} aria-label={`Queue position ${idx + 1}`}>{idx + 1}</span>
                  <div className={styles.info}>
                    <span className={styles.name}>{appt.patientFullName}</span>
                    <span className={styles.meta}>
                      {appt.providerName} &bull;{' '}
                      {new Date(appt.appointmentTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div className={styles.badges}>
                    {appt.isWalkIn && <WalkInBadge size="sm" />}
                    <StatusBadge status={appt.status} />
                  </div>
                </div>

                {/* Keyboard move controls (accessibility fallback) */}
                <div className={styles.moveControls}>
                  <button
                    type="button"
                    className={styles.moveBtn}
                    onClick={() => moveItem(idx, -1)}
                    disabled={idx === 0 || saving}
                    aria-label={`Move ${appt.patientFullName} up`}
                    title="Move up"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    className={styles.moveBtn}
                    onClick={() => moveItem(idx, 1)}
                    disabled={idx === localItems.length - 1 || saving}
                    aria-label={`Move ${appt.patientFullName} down`}
                    title="Move down"
                  >
                    ↓
                  </button>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
