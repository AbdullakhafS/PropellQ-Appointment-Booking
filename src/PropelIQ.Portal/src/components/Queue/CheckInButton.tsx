import { useState } from 'react';
import { queueApi } from '../../api/queueApi';
import styles from './CheckInButton.module.css';

interface CheckInButtonProps {
  appointmentId: string;
  status: string;
  onCheckInSuccess: (appointmentId: string, arrivedAt: string) => void;
}

/**
 * Displays a "Check In" button for eligible (scheduled) appointments only.
 * Prevents duplicate submissions and shows clear success/error feedback.
 */
export function CheckInButton({ appointmentId, status, onCheckInSuccess }: CheckInButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  // Only show for schedulable appointments (task_037_001)
  if (status !== 'scheduled') return null;
  if (done) return <span className={styles.checked} aria-label="Patient checked in">✓ Checked In</span>;

  const handleClick = async () => {
    if (loading) return; // Prevent duplicate submission
    setLoading(true);
    setError(null);

    try {
      const result = await queueApi.checkIn(appointmentId);
      setDone(true);
      onCheckInSuccess(result.appointmentId, result.arrivedAt);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        setError('Patient is already checked in or appointment cannot be checked in.');
      } else {
        setError('Check-in failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.wrapper}>
      <button
        type="button"
        className={styles.btn}
        onClick={handleClick}
        disabled={loading}
        aria-disabled={loading}
        aria-label="Check in patient"
      >
        {loading ? 'Checking In…' : 'Check In'}
      </button>
      {error && (
        <span className={styles.error} role="alert">{error}</span>
      )}
    </div>
  );
}
