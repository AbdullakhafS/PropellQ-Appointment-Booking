import React, { useState, useEffect, useCallback } from 'react';
import { insuranceReviewApi } from '../../api/insuranceReviewApi';
import type {
  PendingInsuranceRow,
  AuditEntry,
  VerificationMethod,
  VerificationStatus,
} from '../../types/insuranceReview';
import styles from './VerificationSidePanel.module.css';

const METHODS: { value: VerificationMethod; label: string }[] = [
  { value: 'phone', label: 'Phone' },
  { value: 'email', label: 'Email' },
  { value: 'portal', label: 'Insurance Portal' },
];

const STATUSES: { value: VerificationStatus; label: string }[] = [
  { value: 'verified', label: 'Verified' },
  { value: 'manual_review', label: 'Needs Manual Review' },
];

interface VerificationSidePanelProps {
  row: PendingInsuranceRow;
  staffId: number;
  onClose: () => void;
  onVerifySuccess: () => void;
}

export function VerificationSidePanel({
  row,
  staffId,
  onClose,
  onVerifySuccess,
}: VerificationSidePanelProps) {
  const [newStatus, setNewStatus] = useState<VerificationStatus>('verified');
  const [method, setMethod] = useState<VerificationMethod>('phone');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [auditHistory, setAuditHistory] = useState<AuditEntry[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);

  const loadAudit = useCallback(async () => {
    setAuditLoading(true);
    try {
      const entries = await insuranceReviewApi.getAuditHistory(row.id);
      setAuditHistory(entries);
    } catch {
      /* non-fatal */
    } finally {
      setAuditLoading(false);
    }
  }, [row.id]);

  useEffect(() => { loadAudit(); }, [loadAudit]);

  // Trap focus: close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      await insuranceReviewApi.verify(row.id, { staffId, newStatus, verificationMethod: method, notes: notes || undefined });
      onVerifySuccess();
    } catch {
      setFormError('Failed to update. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className={styles.overlay} onClick={onClose} aria-hidden="true" />
      <aside
        className={styles.panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby="panel-heading"
      >
        <div className={styles.panelHeader}>
          <h2 id="panel-heading" className={styles.panelTitle}>
            Insurance Verification
            <span className={styles.panelId}> #{row.id}</span>
          </h2>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={onClose}
            aria-label="Close panel"
          >
            ✕
          </button>
        </div>

        <div className={styles.panelBody}>
          {/* Patient & insurance details */}
          <section className={styles.section} aria-labelledby="details-heading">
            <h3 id="details-heading" className={styles.sectionTitle}>Details</h3>
            <dl className={styles.detailGrid}>
              <dt>Patient ID</dt>
              <dd>{row.patientId}</dd>
              <dt>Patient Name</dt>
              <dd>{row.patientName ?? '—'}</dd>
              <dt>Insurance Name</dt>
              <dd>{row.insuranceName ?? '—'}</dd>
              <dt>Member ID</dt>
              <dd><code>{row.memberId ?? '—'}</code></dd>
              <dt>Matched Plan</dt>
              <dd>{row.matchedPlanName ?? <em>No match</em>}</dd>
              <dt>Confidence Score</dt>
              <dd>
                <span className={`${styles.scoreBadge} ${row.confidenceScore >= 70 ? styles.scoreGreen : styles.scoreAmber}`}>
                  {row.confidenceScore}%
                </span>
              </dd>
              <dt>Current Status</dt>
              <dd>
                <span className={`${styles.statusBadge} ${row.verificationStatus === 'verified' ? styles.statusVerified : styles.statusUnverified}`}>
                  {row.verificationStatus.replace('_', ' ')}
                </span>
              </dd>
              <dt>Created</dt>
              <dd>{new Date(row.createdAt).toLocaleString()}</dd>
              {row.lastVerifiedAt && (
                <>
                  <dt>Last Verified</dt>
                  <dd>{new Date(row.lastVerifiedAt).toLocaleString()}</dd>
                </>
              )}
            </dl>
          </section>

          {/* Manual verification form */}
          <section className={styles.section} aria-labelledby="verify-heading">
            <h3 id="verify-heading" className={styles.sectionTitle}>Manual Verification</h3>
            <form onSubmit={handleSubmit} noValidate>
              {formError && (
                <div className={styles.formError} role="alert">{formError}</div>
              )}

              <div className={styles.field}>
                <label htmlFor="new-status" className={styles.label}>New Status</label>
                <select
                  id="new-status"
                  className={styles.select}
                  value={newStatus}
                  onChange={e => setNewStatus(e.target.value as VerificationStatus)}
                >
                  {STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>

              <div className={styles.field}>
                <label htmlFor="method" className={styles.label}>Verification Method</label>
                <select
                  id="method"
                  className={styles.select}
                  value={method}
                  onChange={e => setMethod(e.target.value as VerificationMethod)}
                >
                  {METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </div>

              <div className={styles.field}>
                <label htmlFor="notes" className={styles.label}>Notes <span className={styles.optional}>(optional)</span></label>
                <textarea
                  id="notes"
                  className={styles.textarea}
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  rows={3}
                  placeholder="e.g. Confirmed with patient by phone. Member ID is valid."
                />
              </div>

              <button
                type="submit"
                className={styles.submitBtn}
                disabled={submitting}
                aria-disabled={submitting}
              >
                {submitting ? 'Saving…' : '✓ Mark as Verified'}
              </button>
            </form>
          </section>

          {/* Audit history */}
          <section className={styles.section} aria-labelledby="audit-heading">
            <h3 id="audit-heading" className={styles.sectionTitle}>Audit History</h3>
            {auditLoading ? (
              <p className={styles.auditLoading}>Loading…</p>
            ) : auditHistory.length === 0 ? (
              <p className={styles.auditEmpty}>No verification history yet.</p>
            ) : (
              <ol className={styles.timeline} reversed>
                {auditHistory.map(entry => (
                  <li key={entry.id} className={styles.timelineEntry}>
                    <span className={styles.timelineDot} aria-hidden="true" />
                    <div className={styles.timelineContent}>
                      <p className={styles.timelineMain}>
                        Staff #{entry.verifiedByStaffId} changed status from{' '}
                        <strong>{entry.previousStatus}</strong> to{' '}
                        <strong>{entry.newStatus}</strong> via {entry.verificationMethod}
                      </p>
                      {entry.notes && <p className={styles.timelineNotes}>{entry.notes}</p>}
                      <time className={styles.timelineTime} dateTime={entry.verifiedAt}>
                        {new Date(entry.verifiedAt).toLocaleString()}
                      </time>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      </aside>
    </>
  );
}
