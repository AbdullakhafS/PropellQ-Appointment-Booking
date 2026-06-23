import { useState, useEffect, useCallback } from 'react';
import { appointmentApi } from '../../api/appointmentApi';
import type { AppointmentDetail } from '../../types/appointmentDetail';
import { WalkInBadge } from '../WalkIn/WalkInBadge';
import styles from './AppointmentDetailPanel.module.css';

interface AppointmentDetailPanelProps {
  appointmentId: string;
  onClose: () => void;
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

export function AppointmentDetailPanel({ appointmentId, onClose }: AppointmentDetailPanelProps) {
  const [detail, setDetail] = useState<AppointmentDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await appointmentApi.getDetail(appointmentId);
      setDetail(data);
    } catch {
      setError('Failed to load appointment details.');
    } finally {
      setLoading(false);
    }
  }, [appointmentId]);

  useEffect(() => { load(); }, [load]);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <>
      <div className={styles.overlay} onClick={onClose} aria-hidden="true" />
      <aside
        className={styles.panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-heading"
      >
        <div className={styles.panelHeader}>
          <h2 id="detail-heading" className={styles.panelTitle}>Appointment Detail</h2>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className={styles.panelBody}>
          {loading && (
            <div className={styles.centred} role="status" aria-live="polite">
              <div className={styles.spinner} aria-hidden="true" />
              Loading…
            </div>
          )}

          {error && (
            <div className={styles.errorState} role="alert">
              {error}
              <button type="button" className={styles.retryBtn} onClick={load}>Retry</button>
            </div>
          )}

          {detail && (
            <>
              {/* Metadata */}
              <section className={styles.section} aria-labelledby="meta-heading">
                <h3 id="meta-heading" className={styles.sectionTitle}>Patient & Appointment</h3>
                <dl className={styles.dl}>
                  <dt>Patient</dt>
                  <dd>{detail.patientFullName}</dd>

                  <dt>Provider</dt>
                  <dd>{detail.providerName}</dd>

                  <dt>Scheduled</dt>
                  <dd>
                    <time dateTime={detail.appointmentTime}>
                      {new Date(detail.appointmentTime).toLocaleString([], {
                        weekday: 'short', month: 'short', day: 'numeric',
                        hour: '2-digit', minute: '2-digit',
                      })}
                    </time>
                  </dd>

                  <dt>Duration</dt>
                  <dd>{detail.durationMinutes} min</dd>

                  <dt>Type</dt>
                  <dd>{detail.isWalkIn ? <WalkInBadge size="sm" /> : 'Pre-Booked'}</dd>

                  <dt>Status</dt>
                  <dd><StatusBadge status={detail.status} /></dd>

                  {/* Arrival timestamp — task_038_001/003/004 */}
                  <dt>Arrived (UTC)</dt>
                  <dd>
                    {detail.arrivedAt
                      ? (
                        <time dateTime={detail.arrivedAt} className={styles.arrivedAt}>
                          ✓ {new Date(detail.arrivedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                          {' '}
                          <span className={styles.arrivedDate}>
                            ({new Date(detail.arrivedAt).toLocaleDateString()})
                          </span>
                        </time>
                      )
                      : <span className={styles.notArrived}>Not yet arrived</span>}
                  </dd>
                </dl>
              </section>

              {/* Status history (task_038_002 — audit trail) */}
              <section className={styles.section} aria-labelledby="history-heading">
                <h3 id="history-heading" className={styles.sectionTitle}>Status History</h3>
                {detail.statusHistory.length === 0 ? (
                  <p className={styles.emptyHistory}>No status changes recorded.</p>
                ) : (
                  <ol className={styles.timeline} reversed>
                    {[...detail.statusHistory].reverse().map(entry => (
                      <li key={entry.id} className={styles.timelineItem}>
                        <span className={styles.dot} aria-hidden="true" />
                        <div className={styles.timelineContent}>
                          <p className={styles.transition}>
                            <StatusBadge status={entry.previousStatus} />
                            {' → '}
                            <StatusBadge status={entry.newStatus} />
                          </p>
                          <time className={styles.transitionTime} dateTime={entry.transitionedAtUtc}>
                            {new Date(entry.transitionedAtUtc).toLocaleString([], {
                              month: 'short', day: 'numeric',
                              hour: '2-digit', minute: '2-digit', second: '2-digit',
                            })} UTC
                          </time>
                          {entry.notes && <p className={styles.transitionNote}>{entry.notes}</p>}
                        </div>
                      </li>
                    ))}
                  </ol>
                )}
              </section>
            </>
          )}
        </div>
      </aside>
    </>
  );
}
