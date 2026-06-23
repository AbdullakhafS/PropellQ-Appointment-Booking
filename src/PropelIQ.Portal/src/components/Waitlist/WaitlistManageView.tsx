import { useState, useEffect, useCallback } from 'react';
import { waitlistApi } from '../../api/waitlistApi';
import { WaitlistOfferPanel } from './WaitlistOfferPanel';
import type { WaitlistEntry, WaitlistOffer } from '../../types/waitlist';
import styles from './WaitlistManageView.module.css';

const STATUS_COLORS: Record<string, string> = {
  queued: styles.tagQueued,
  offered: styles.tagOffered,
  fulfilled: styles.tagFulfilled,
  cancelled: styles.tagCancelled,
};

interface WaitlistManageViewProps {
  providerId?: string;
}

export function WaitlistManageView({ providerId }: WaitlistManageViewProps) {
  const [entries, setEntries] = useState<WaitlistEntry[]>([]);
  const [pendingOffers, setPendingOffers] = useState<WaitlistOffer[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [e, o] = await Promise.all([
        waitlistApi.getEntries(providerId),
        waitlistApi.getPendingOffers(),
      ]);
      setEntries(e);
      setPendingOffers(o);
    } catch {
      setError('Failed to load waitlist data.');
    } finally {
      setLoading(false);
    }
  }, [providerId]);

  useEffect(() => { load(); }, [load]);

  // Poll for expiry processing every 60 s
  useEffect(() => {
    const timer = setInterval(async () => {
      await waitlistApi.processExpired();
      await load();
    }, 60_000);
    return () => clearInterval(timer);
  }, [load]);

  const handleCancel = async (entryId: string) => {
    await waitlistApi.cancel(entryId);
    showToast('Waitlist entry cancelled.');
    await load();
  };

  const handleOfferResponded = async (
    offerId: string, accepted: boolean, appointmentId: string | null
  ) => {
    setPendingOffers(prev => prev.filter(o => o.offerId !== offerId));
    if (accepted && appointmentId) {
      showToast('Appointment confirmed! The patient has been scheduled.');
    } else {
      showToast('Offer declined. Next eligible patient will be notified.');
    }
    await load();
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h2 className={styles.title}>Waitlist Management</h2>
        <div className={styles.headerRight}>
          <span className={styles.summary}>{entries.length} active</span>
          <button type="button" className={styles.refreshBtn} onClick={load} disabled={loading}>
            {loading ? '…' : '↻ Refresh'}
          </button>
        </div>
      </header>

      {toast && <div className={styles.toast} role="status" aria-live="polite">{toast}</div>}
      {error && <div className={styles.errorBanner} role="alert">{error}</div>}

      {/* Pending offers */}
      {pendingOffers.length > 0 && (
        <section className={styles.section} aria-labelledby="offers-heading">
          <h3 id="offers-heading" className={styles.sectionTitle}>Pending Offers</h3>
          <div className={styles.offerList}>
            {pendingOffers.map(offer => (
              <WaitlistOfferPanel
                key={offer.offerId}
                offer={offer}
                onResponded={handleOfferResponded}
              />
            ))}
          </div>
        </section>
      )}

      {/* Waitlist entries table */}
      <section className={styles.section} aria-labelledby="entries-heading">
        <h3 id="entries-heading" className={styles.sectionTitle}>Waitlist Queue</h3>

        {entries.length === 0 ? (
          <div className={styles.empty} role="status">
            <p className={styles.emptyIcon} aria-hidden="true">📋</p>
            <p className={styles.emptyTitle}>No patients on waitlist</p>
          </div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.table} aria-label="Waitlist entries">
              <thead>
                <tr>
                  <th scope="col" className={styles.th}>#</th>
                  <th scope="col" className={styles.th}>Patient</th>
                  <th scope="col" className={styles.th}>Provider</th>
                  <th scope="col" className={styles.th}>Status</th>
                  <th scope="col" className={styles.th}>Joined</th>
                  <th scope="col" className={styles.th}>Action</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry, idx) => (
                  <tr key={entry.waitlistEntryId} className={styles.tr}>
                    <td className={styles.td}>{idx + 1}</td>
                    <td className={styles.td}>
                      <span className={styles.patientName}>{entry.patientFullName}</span>
                    </td>
                    <td className={styles.td}>{entry.providerName}</td>
                    <td className={styles.td}>
                      <span className={`${styles.statusTag} ${STATUS_COLORS[entry.status] ?? ''}`}>
                        {entry.status}
                      </span>
                    </td>
                    <td className={styles.td}>
                      <time dateTime={entry.createdAt}>
                        {new Date(entry.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </time>
                    </td>
                    <td className={styles.td}>
                      {entry.status === 'queued' && (
                        <button
                          type="button"
                          className={styles.cancelBtn}
                          onClick={() => handleCancel(entry.waitlistEntryId)}
                          aria-label={`Remove ${entry.patientFullName} from waitlist`}
                        >
                          Remove
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
