import { useQueueStats } from '../../hooks/useQueueStats';
import type { WaitHealth } from '../../types/queueStats';
import styles from './QueueStatsPanel.module.css';

interface QueueStatsPanelProps {
  /** Increment this value to trigger a stats refresh (e.g. after SSE queue events). */
  refreshTrigger?: number;
}

function WaitHealthLabel({ health }: { health: WaitHealth }) {
  const cls =
    health === 'Critical' ? styles.healthCritical :
    health === 'Warning'  ? styles.healthWarning  :
    styles.healthNormal;

  const label =
    health === 'Critical' ? '🔴 High' :
    health === 'Warning'  ? '🟡 Elevated' :
    '🟢 Normal';

  return (
    <span className={`${styles.healthBadge} ${cls}`} aria-label={`Wait time health: ${health}`}>
      {label}
    </span>
  );
}

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: boolean;
}

function StatCard({ label, value, sub, accent }: StatCardProps) {
  return (
    <div className={`${styles.card} ${accent ? styles.cardAccent : ''}`}>
      <div className={styles.cardValue} aria-label={`${label}: ${value}`}>{value}</div>
      <div className={styles.cardLabel}>{label}</div>
      {sub && <div className={styles.cardSub}>{sub}</div>}
    </div>
  );
}

export function QueueStatsPanel({ refreshTrigger = 0 }: QueueStatsPanelProps) {
  const { stats, loading, error, refresh } = useQueueStats({ refreshTrigger });

  return (
    <section
      className={styles.panel}
      aria-labelledby="stats-heading"
      aria-live="polite"
    >
      <div className={styles.panelHeader}>
        <h3 id="stats-heading" className={styles.heading}>Queue Overview</h3>
        <div className={styles.headerRight}>
          {stats && <WaitHealthLabel health={stats.waitHealth} />}
          <button
            type="button"
            className={styles.refreshBtn}
            onClick={refresh}
            disabled={loading}
            aria-label="Refresh queue statistics"
          >
            {loading ? '…' : '↻'}
          </button>
        </div>
      </div>

      {error && (
        <div className={styles.error} role="alert">{error}</div>
      )}

      {!stats && !loading && !error && (
        <div className={styles.empty}>No statistics available.</div>
      )}

      {stats && (
        <>
          <div className={styles.cards}>
            <StatCard
              label="Active Patients"
              value={stats.activePatientCount}
              sub={`${stats.arrivedCount} checked in`}
            />
            <StatCard
              label="Walk-Ins"
              value={stats.walkInCount}
            />
            <StatCard
              label="Avg Wait"
              value={`${stats.averageWaitMinutes} min`}
              sub={stats.waitHealth !== 'Normal'
                ? `Threshold: ${stats.waitWarningThreshold} min`
                : undefined}
              accent={stats.waitHealth !== 'Normal'}
            />
            <StatCard
              label="Max Wait"
              value={`${stats.maxWaitMinutes} min`}
            />
          </div>

          {stats.waitHealth !== 'Normal' && (
            <div
              className={`${styles.alert} ${stats.waitHealth === 'Critical' ? styles.alertCritical : styles.alertWarning}`}
              role="alert"
            >
              <strong>
                {stats.waitHealth === 'Critical'
                  ? 'Critical: '
                  : 'Warning: '}
              </strong>
              Average wait time ({stats.averageWaitMinutes} min) exceeds the{' '}
              {stats.waitHealth === 'Critical' ? 'critical' : 'warning'} threshold
              ({stats.waitHealth === 'Critical'
                ? stats.waitCriticalThreshold
                : stats.waitWarningThreshold} min).
              Consider adding staff or expediting patients.
            </div>
          )}

          <p className={styles.updatedAt}>
            Updated{' '}
            <time dateTime={stats.computedAt}>
              {new Date(stats.computedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </time>
          </p>
        </>
      )}
    </section>
  );
}
