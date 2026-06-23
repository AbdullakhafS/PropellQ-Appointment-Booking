import { useState } from 'react';
import { waitlistApi } from '../../api/waitlistApi';
import type { JoinWaitlistRequest } from '../../types/waitlist';
import styles from './WaitlistJoinButton.module.css';

interface WaitlistJoinButtonProps {
  patientId: string;
  patientFullName: string;
  providerId: string;
  providerName: string;
  clinicId?: string;
  onJoined?: (entryId: string) => void;
}

/**
 * Renders a "Join Waitlist" button for when a slot is full.
 * Idempotent — if the patient is already on the waitlist it shows "On Waitlist".
 */
export function WaitlistJoinButton({
  patientId, patientFullName, providerId, providerName, clinicId, onJoined,
}: WaitlistJoinButtonProps) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'joined' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  const handleClick = async () => {
    if (status === 'loading' || status === 'joined') return;
    setStatus('loading');
    setError(null);

    const request: JoinWaitlistRequest = {
      patientId, patientFullName, providerId, providerName, clinicId,
    };

    try {
      const entry = await waitlistApi.join(request);
      setStatus('joined');
      onJoined?.(entry.waitlistEntryId);
    } catch {
      setStatus('error');
      setError('Failed to join waitlist. Please try again.');
    }
  };

  if (status === 'joined') {
    return (
      <span className={styles.joined} aria-label="Added to waitlist">
        ✓ On Waitlist
      </span>
    );
  }

  return (
    <div className={styles.wrapper}>
      <button
        type="button"
        className={styles.btn}
        onClick={handleClick}
        disabled={status === 'loading'}
        aria-disabled={status === 'loading'}
        aria-label="Join waitlist for this provider"
      >
        {status === 'loading' ? 'Joining…' : 'Join Waitlist'}
      </button>
      {error && <span className={styles.error} role="alert">{error}</span>}
    </div>
  );
}
