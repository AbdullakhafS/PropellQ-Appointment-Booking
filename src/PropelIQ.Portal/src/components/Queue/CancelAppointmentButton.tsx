import { useState } from 'react';
import { queueApi } from '../../api/queueApi';
import styles from './CancelAppointmentButton.module.css';

interface CancelAppointmentButtonProps {
  appointmentId: string;
  patientName: string;
  onCancelled: (appointmentId: string) => void;
}

/**
 * Cancels a scheduled/arrived appointment.
 * Shows a confirmation dialog before calling the API.
 * On success the parent is notified so the queue list can refresh.
 * Releasing the slot automatically triggers the auto-offer pipeline on the server.
 */
export function CancelAppointmentButton({
  appointmentId,
  patientName,
  onCancelled,
}: CancelAppointmentButtonProps) {
  const [confirming, setConfirming] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCancel = async () => {
    setCancelling(true);
    setError(null);
    try {
      await queueApi.cancelAppointment(appointmentId);
      onCancelled(appointmentId);
    } catch {
      setError('Cancel failed. Please try again.');
      setCancelling(false);
    }
  };

  if (confirming) {
    return (
      <div className={styles.confirmBox} role="dialog" aria-modal="true" aria-labelledby="confirm-label">
        <p id="confirm-label" className={styles.confirmMsg}>
          Cancel appointment for <strong>{patientName}</strong>? The waitlist will be offered this slot automatically.
        </p>
        {error && <p className={styles.error} role="alert">{error}</p>}
        <div className={styles.confirmActions}>
          <button
            type="button"
            className={styles.confirmYes}
            onClick={handleCancel}
            disabled={cancelling}
            aria-disabled={cancelling}
          >
            {cancelling ? 'Cancelling…' : 'Yes, Cancel'}
          </button>
          <button
            type="button"
            className={styles.confirmNo}
            onClick={() => { setConfirming(false); setError(null); }}
            disabled={cancelling}
          >
            Keep
          </button>
        </div>
      </div>
    );
  }

  return (
    <button
      type="button"
      className={styles.cancelBtn}
      onClick={() => setConfirming(true)}
      aria-label={`Cancel appointment for ${patientName}`}
    >
      Cancel
    </button>
  );
}
