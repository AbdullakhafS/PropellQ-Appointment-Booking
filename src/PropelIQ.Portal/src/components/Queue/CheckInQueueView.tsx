import { useEffect, useCallback, useState } from 'react';
import { queueApi } from '../../api/queueApi';
import { useQueueSse } from '../../hooks/useQueueSse';
import { WalkInBadge } from '../WalkIn/WalkInBadge';
import { CheckInButton } from './CheckInButton';
import type { QueueAppointment } from '../../types/queue';
import styles from './CheckInQueueView.module.css';

// ---- Helpers ----

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

function ArrivalTime({ arrivedAt }: { arrivedAt: string | null }) {
  if (!arrivedAt) return null;
  return (
    <span className={styles.arrivalTime} aria-label={`Arrived at ${new Date(arrivedAt).toLocaleTimeString()}`}>
      ✓ {new Date(arrivedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
    </span>
  );
}

// ---- Main component ----

interface CheckInQueueViewProps {
  date?: string;
}

export function CheckInQueueView({ date }: CheckInQueueViewProps) {
  const { items: liveItems, connectionStatus, setInitialItems } = useQueueSse();
  const [localItems, setLocalItems] = useState<QueueAppointment[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  // Sync SSE to local
  useEffect(() => { setLocalItems(liveItems); }, [liveItems]);

  const loadSnapshot = useCallback(async () => {
    try {
      const result = await queueApi.getQueue({ date });
      setInitialItems(result.items, result.version);
      setLocalItems(result.items);
    } catch { /* non-fatal */ }
  }, [date, setInitialItems]);

  useEffect(() => { loadSnapshot(); }, [loadSnapshot]);

  const handleCheckInSuccess = useCallback((appointmentId: string, arrivedAt: string) => {
    // Optimistically update local state (SSE will also deliver the same update)
    setLocalItems(prev => prev.map(a =>
      a.appointmentId === appointmentId
        ? { ...a, status: 'arrived' as const, arrivedAt }
        : a
    ));
    setToast('Patient checked in successfully.');
    setTimeout(() => setToast(null), 3000);
  }, []);

  const connLabel =
    connectionStatus === 'connected' ? 'Live' :
    connectionStatus === 'reconnecting' ? 'Reconnecting…' : 'Connecting…';

  const connCls =
    connectionStatus === 'connected' ? styles.connGreen :
    connectionStatus === 'reconnecting' ? styles.connAmber :
    styles.connGrey;

  const arrivedCount = localItems.filter(a => a.status === 'arrived').length;
  const scheduledCount = localItems.filter(a => a.status === 'scheduled').length;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h2 className={styles.title}>Patient Check-In</h2>
          <span className={`${styles.connBadge} ${connCls}`} aria-live="polite">
            <span className={styles.connDot} aria-hidden="true" />
            {connLabel}
          </span>
        </div>
        <p className={styles.summary}>
          {scheduledCount} awaiting · {arrivedCount} checked in
        </p>
      </header>

      {toast && (
        <div className={styles.toast} role="status" aria-live="polite">{toast}</div>
      )}

      {localItems.length === 0 ? (
        <div className={styles.empty} role="status">
          <p className={styles.emptyIcon} aria-hidden="true">📋</p>
          <p className={styles.emptyTitle}>No appointments in queue</p>
          <p className={styles.emptySub}>New appointments will appear automatically.</p>
        </div>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table} aria-label="Check-in queue" aria-live="polite">
            <thead>
              <tr>
                <th scope="col" className={styles.th}>Time</th>
                <th scope="col" className={styles.th}>Patient</th>
                <th scope="col" className={styles.th}>Provider</th>
                <th scope="col" className={styles.th}>Type</th>
                <th scope="col" className={styles.th}>Status</th>
                <th scope="col" className={styles.th}>Arrived</th>
                <th scope="col" className={styles.th}>Action</th>
              </tr>
            </thead>
            <tbody>
              {localItems.map(appt => (
                <tr
                  key={appt.appointmentId}
                  className={`${styles.tr} ${appt.status === 'arrived' ? styles.trArrived : ''} ${appt.isWalkIn ? styles.trWalkIn : ''}`}
                >
                  <td className={styles.td}>
                    <time dateTime={appt.appointmentTime}>
                      {new Date(appt.appointmentTime).toLocaleTimeString([], {
                        hour: '2-digit', minute: '2-digit',
                      })}
                    </time>
                  </td>
                  <td className={styles.td}>
                    <span className={styles.patientName}>{appt.patientFullName}</span>
                  </td>
                  <td className={styles.td}>{appt.providerName}</td>
                  <td className={styles.td}>
                    {appt.isWalkIn
                      ? <WalkInBadge size="sm" />
                      : <span className={styles.preBooked}>Pre-Booked</span>}
                  </td>
                  <td className={styles.td}>
                    <StatusBadge status={appt.status} />
                  </td>
                  <td className={styles.td}>
                    <ArrivalTime arrivedAt={appt.arrivedAt} />
                  </td>
                  <td className={styles.td}>
                    <CheckInButton
                      appointmentId={appt.appointmentId}
                      status={appt.status}
                      onCheckInSuccess={handleCheckInSuccess}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
