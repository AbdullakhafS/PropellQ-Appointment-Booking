import { useState, useEffect, useRef } from 'react';
import { waitlistApi } from '../../api/waitlistApi';
import type { WaitlistOffer } from '../../types/waitlist';
import styles from './WaitlistOfferPanel.module.css';

interface WaitlistOfferPanelProps {
  offer: WaitlistOffer;
  onResponded: (offerId: string, accepted: boolean, appointmentId: string | null) => void;
}

/**
 * Displays a pending waitlist offer with countdown timer and Accept/Decline controls.
 */
export function WaitlistOfferPanel({ offer, onResponded }: WaitlistOfferPanelProps) {
  const [responding, setResponding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const update = () => {
      const diff = Math.max(0, Math.round((new Date(offer.expiresAt).getTime() - Date.now()) / 1000));
      setRemainingSeconds(diff);
      if (diff === 0 && timerRef.current) clearInterval(timerRef.current);
    };
    update();
    timerRef.current = setInterval(update, 1000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [offer.expiresAt]);

  const isExpired = remainingSeconds === 0;
  const mins = Math.floor(remainingSeconds / 60);
  const secs = remainingSeconds % 60;
  const countdownLabel = `${mins}:${secs.toString().padStart(2, '0')}`;

  const handleRespond = async (isAccept: boolean) => {
    if (responding || isExpired) return;
    setResponding(true);
    setError(null);
    try {
      const result = await waitlistApi.respond(offer.offerId, isAccept);
      onResponded(offer.offerId, isAccept, result.appointmentId);
    } catch {
      setError('Response failed. Please try again.');
    } finally {
      setResponding(false);
    }
  };

  return (
    <div
      className={`${styles.panel} ${isExpired ? styles.expired : ''}`}
      role="dialog"
      aria-labelledby="offer-heading"
      aria-live="assertive"
    >
      <h3 id="offer-heading" className={styles.heading}>
        Appointment Offer Available
      </h3>

      <dl className={styles.dl}>
        <dt>Provider</dt>
        <dd>{offer.providerName}</dd>
        <dt>Slot Time</dt>
        <dd>
          <time dateTime={offer.slotStartTime}>
            {new Date(offer.slotStartTime).toLocaleString([], {
              weekday: 'short', month: 'short', day: 'numeric',
              hour: '2-digit', minute: '2-digit',
            })}
          </time>
        </dd>
        <dt>Expires In</dt>
        <dd className={`${styles.countdown} ${remainingSeconds <= 300 ? styles.countdownWarning : ''}`}>
          {isExpired ? 'Expired' : countdownLabel}
        </dd>
      </dl>

      {error && <div className={styles.error} role="alert">{error}</div>}

      {isExpired ? (
        <p className={styles.expiredMsg}>This offer has expired. A new offer will be issued automatically.</p>
      ) : (
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.acceptBtn}
            onClick={() => handleRespond(true)}
            disabled={responding}
            aria-disabled={responding}
          >
            {responding ? 'Accepting…' : 'Accept Appointment'}
          </button>
          <button
            type="button"
            className={styles.declineBtn}
            onClick={() => handleRespond(false)}
            disabled={responding}
            aria-disabled={responding}
          >
            Decline
          </button>
        </div>
      )}
    </div>
  );
}
