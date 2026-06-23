import { useState, useEffect, useCallback } from 'react';
import { queueApi } from '../../api/queueApi';
import type { QueueAppointment, QueueFilter } from '../../types/queue';
import { WalkInBadge } from '../WalkIn/WalkInBadge';
import styles from './QueueView.module.css';

type FilterMode = 'all' | 'walkin' | 'prebooked';

const STATUS_LABELS: Record<string, string> = {
  scheduled: 'Scheduled',
  arrived: 'Arrived',
  completed: 'Completed',
  cancelled: 'Cancelled',
};

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === 'arrived' ? styles.statusArrived :
    status === 'completed' ? styles.statusCompleted :
    status === 'cancelled' ? styles.statusCancelled :
    styles.statusScheduled;
  return <span className={`${styles.statusBadge} ${cls}`}>{STATUS_LABELS[status] ?? status}</span>;
}

interface QueueViewProps {
  date?: string;
}

export function QueueView({ date }: QueueViewProps) {
  const [items, setItems] = useState<QueueAppointment[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [hasWalkIns, setHasWalkIns] = useState(false);
  const [filterMode, setFilterMode] = useState<FilterMode>('all');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pageSize = 20;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    const filter: QueueFilter = {
      date,
      page,
      pageSize,
    };

    if (filterMode === 'walkin') filter.isWalkIn = true;
    else if (filterMode === 'prebooked') filter.isWalkIn = false;

    try {
      const result = await queueApi.getQueue(filter);
      setItems(result.items);
      setTotalCount(result.totalCount);
      setHasWalkIns(result.hasWalkIns);
    } catch {
      setError('Failed to load appointment queue. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [date, filterMode, page]);

  useEffect(() => { load(); }, [load]);

  const handleFilterChange = (mode: FilterMode) => {
    setFilterMode(mode);
    setPage(1);
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h2 className={styles.title}>
          Appointment Queue
          {date && <span className={styles.dateLabel}> — {date}</span>}
        </h2>
        <p className={styles.summary}>
          {loading ? 'Loading…' : `${totalCount} appointment${totalCount !== 1 ? 's' : ''}`}
          {hasWalkIns && !loading && <> · <span className={styles.walkInSummary}>includes walk-ins</span></>}
        </p>
      </header>

      {/* Walk-in filter (task_033_004) */}
      <div className={styles.filterBar} role="group" aria-label="Filter appointments">
        {(
          [
            { mode: 'all', label: 'All' },
            { mode: 'walkin', label: 'Walk-Ins Only' },
            { mode: 'prebooked', label: 'Pre-Booked Only' },
          ] as { mode: FilterMode; label: string }[]
        ).map(({ mode, label }) => (
          <button
            key={mode}
            type="button"
            className={`${styles.filterBtn} ${filterMode === mode ? styles.filterBtnActive : ''}`}
            onClick={() => handleFilterChange(mode)}
            aria-pressed={filterMode === mode}
          >
            {label}
          </button>
        ))}
        <button
          type="button"
          className={styles.refreshBtn}
          onClick={load}
          disabled={loading}
          aria-label="Refresh queue"
        >
          {loading ? '…' : '↻'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className={styles.errorBanner} role="alert">
          {error}
          <button type="button" className={styles.retryBtn} onClick={load}>Retry</button>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && items.length === 0 && (
        <div className={styles.emptyState} role="status">
          <p className={styles.emptyIcon} aria-hidden="true">📋</p>
          <p className={styles.emptyTitle}>No appointments</p>
          <p className={styles.emptySubtitle}>
            {filterMode === 'walkin'
              ? 'No walk-in appointments match the current filter.'
              : 'No appointments found for the selected criteria.'}
          </p>
        </div>
      )}

      {/* Queue table */}
      {!error && items.length > 0 && (
        <div className={styles.tableWrapper}>
          <table className={styles.table} aria-label="Appointment queue">
            <thead>
              <tr>
                <th scope="col" className={styles.th}>Time</th>
                <th scope="col" className={styles.th}>Patient</th>
                <th scope="col" className={styles.th}>Provider</th>
                <th scope="col" className={styles.th}>Duration</th>
                <th scope="col" className={styles.th}>Type</th>
                <th scope="col" className={styles.th}>Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map(appt => (
                <tr
                  key={appt.appointmentId}
                  className={`${styles.tr} ${appt.isWalkIn ? styles.trWalkIn : ''}`}
                >
                  <td className={styles.td}>
                    <time dateTime={appt.appointmentTime}>
                      {new Date(appt.appointmentTime).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </time>
                  </td>
                  <td className={styles.td}>{appt.patientFullName}</td>
                  <td className={styles.td}>{appt.providerName}</td>
                  <td className={styles.td}>{appt.durationMinutes} min</td>
                  <td className={styles.td}>
                    {appt.isWalkIn
                      ? <WalkInBadge size="sm" />
                      : <span className={styles.preBooked}>Pre-Booked</span>}
                  </td>
                  <td className={styles.td}>
                    <StatusBadge status={appt.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className={styles.pagination}>
          <button
            type="button"
            className={styles.pageBtn}
            disabled={page <= 1}
            onClick={() => setPage(p => Math.max(1, p - 1))}
          >
            ← Previous
          </button>
          <span>Page {page} of {totalPages}</span>
          <button
            type="button"
            className={styles.pageBtn}
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
