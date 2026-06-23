import { useEffect, useCallback } from 'react';
import { queueApi } from '../../api/queueApi';
import { useQueueSse } from '../../hooks/useQueueSse';
import { WalkInBadge } from '../WalkIn/WalkInBadge';
import styles from './RealTimeQueueView.module.css';

type AppStatus = 'scheduled' | 'arrived' | 'completed' | 'cancelled';

const STATUS_LABELS: Record<string, string> = {
  scheduled: 'Scheduled',
  arrived: 'Arrived',
  completed: 'Completed',
  cancelled: 'Cancelled',
};

function ConnectionIndicator({ status }: { status: string }) {
  const cls =
    status === 'connected' ? styles.connGreen :
    status === 'reconnecting' ? styles.connAmber :
    styles.connGrey;

  const label =
    status === 'connected' ? 'Live' :
    status === 'reconnecting' ? 'Reconnecting…' :
    'Connecting…';

  return (
    <span className={`${styles.connBadge} ${cls}`} aria-live="polite" aria-label={`Queue connection: ${label}`}>
      <span className={styles.connDot} aria-hidden="true" />
      {label}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === 'arrived' ? styles.statusArrived :
    status === 'completed' ? styles.statusCompleted :
    status === 'cancelled' ? styles.statusCancelled :
    styles.statusScheduled;
  return <span className={`${styles.statusBadge} ${cls}`}>{STATUS_LABELS[status] ?? status}</span>;
}

function WaitTimeSummary({ appointmentTime }: { appointmentTime: string }) {
  const scheduled = new Date(appointmentTime);
  const now = new Date();
  const diffMs = now.getTime() - scheduled.getTime();
  const diffMin = Math.round(diffMs / 60_000);

  if (diffMin < 0) {
    return <span className={styles.waitUpcoming}>{Math.abs(diffMin)} min</span>;
  }
  if (diffMin === 0) {
    return <span className={styles.waitNow}>Now</span>;
  }
  return (
    <span className={`${styles.waitWaiting} ${diffMin > 15 ? styles.waitLong : ''}`}>
      +{diffMin} min
    </span>
  );
}

interface RealTimeQueueViewProps {
  date?: string;
}

export function RealTimeQueueView({ date }: RealTimeQueueViewProps) {
  const { items, connectionStatus, queueVersion, setInitialItems } = useQueueSse();

  const loadSnapshot = useCallback(async () => {
    try {
      const result = await queueApi.getQueue({ date });
      setInitialItems(result.items, result.version);
    } catch {
      // Non-fatal: SSE will still push live updates
    }
  }, [date, setInitialItems]);

  useEffect(() => { loadSnapshot(); }, [loadSnapshot]);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h2 className={styles.title}>Live Queue</h2>
          <ConnectionIndicator status={connectionStatus} />
        </div>
        {date && <p className={styles.dateLabel}>{date}</p>}
        <p className={styles.summary}>
          {items.length} appointment{items.length !== 1 ? 's' : ''}
          {items.some(i => i.isWalkIn) && ' · includes walk-ins'}
        </p>
      </header>

      {items.length === 0 ? (
        <div className={styles.emptyState} role="status" aria-live="polite">
          <p className={styles.emptyIcon} aria-hidden="true">📋</p>
          <p className={styles.emptyTitle}>Queue is empty</p>
          <p className={styles.emptySubtitle}>New arrivals will appear automatically.</p>
        </div>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table} aria-label="Live appointment queue" aria-live="polite" aria-relevant="additions removals">
            <thead>
              <tr>
                <th scope="col" className={styles.th}>Time</th>
                <th scope="col" className={styles.th}>Patient</th>
                <th scope="col" className={styles.th}>Provider</th>
                <th scope="col" className={styles.th}>Type</th>
                <th scope="col" className={styles.th}>Status</th>
                <th scope="col" className={styles.th}>Wait</th>
              </tr>
            </thead>
            <tbody>
              {items.map(appt => (
                <tr
                  key={appt.appointmentId}
                  className={`${styles.tr} ${appt.isWalkIn ? styles.trWalkIn : ''} ${appt.status === 'arrived' ? styles.trArrived : ''}`}
                >
                  <td className={styles.td}>
                    <time dateTime={appt.appointmentTime}>
                      {new Date(appt.appointmentTime).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
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
                    <WaitTimeSummary appointmentTime={appt.appointmentTime} />
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
