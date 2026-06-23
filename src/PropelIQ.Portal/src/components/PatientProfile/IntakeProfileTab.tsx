import React, { useState, useEffect, useCallback } from 'react';
import { patientIntakeApi } from '../../api/patientIntakeApi';
import type { ProfileIntake } from '../../types/profileIntake';
import { exportIntakePdf } from '../../utils/intakePdfExport';
import styles from './IntakeProfileTab.module.css';

// Minimal re-use: the full edit form is handled via ManualIntakeForm elsewhere.
// Here we display read-only sections with an "Edit" toggle that is gated on canEdit prop.

function VerificationBadge({ status }: { status: string | null }) {
  if (!status) return null;
  const cls =
    status === 'verified' ? styles.badgeGreen :
    status === 'unverified' ? styles.badgeAmber :
    styles.badgeBlue;
  return <span className={`${styles.badge} ${cls}`}>{status.replace('_', ' ')}</span>;
}

function ConfidencePill({ score }: { score: number }) {
  if (score === 100) return null;  // only show when less than perfect
  const cls = score >= 70 ? styles.pillGreen : styles.pillAmber;
  return <span className={`${styles.pill} ${cls}`}>{score}%</span>;
}

interface IntakeProfileTabProps {
  patientId: number;
  /** Set true when the patient's appointment has not yet started */
  canEdit: boolean;
  onEditClick: (intake: ProfileIntake) => void;
}

export function IntakeProfileTab({ patientId, canEdit, onEditClick }: IntakeProfileTabProps) {
  const [intake, setIntake] = useState<ProfileIntake | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await patientIntakeApi.getLatest(patientId);
      setIntake(data);
    } catch {
      setError('Failed to load intake data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  useEffect(() => { load(); }, [load]);

  const handleExport = () => {
    if (intake) exportIntakePdf(intake);
  };

  if (loading) {
    return (
      <div className={styles.centred} role="status" aria-live="polite">
        <div className={styles.spinner} aria-hidden="true" />
        <p>Loading intake…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorState} role="alert">
        <p>{error}</p>
        <button type="button" className={styles.retryBtn} onClick={load}>Retry</button>
      </div>
    );
  }

  if (!intake) {
    return (
      <div className={styles.emptyState} role="status">
        <p className={styles.emptyIcon} aria-hidden="true">📋</p>
        <p className={styles.emptyTitle}>No intake on file</p>
        <p className={styles.emptySubtitle}>Complete intake when booking your next appointment.</p>
      </div>
    );
  }

  const modeLabel = intake.mode === 'ai' ? 'AI Chatbot' : 'Manual Form';

  return (
    <article className={styles.tab} aria-label="Patient intake information">
      {/* Metadata bar */}
      <div className={styles.meta}>
        <span>
          Completed: <strong>{new Date(intake.completedAt).toLocaleString()}</strong>
        </span>
        <span>Via: <strong>{modeLabel}</strong></span>
        {intake.updatedAt !== intake.completedAt && (
          <span>Updated: <strong>{new Date(intake.updatedAt).toLocaleDateString()}</strong></span>
        )}
        <div className={styles.metaActions}>
          {canEdit && (
            <button
              type="button"
              className={styles.editBtn}
              onClick={() => onEditClick(intake)}
              aria-label="Edit intake information"
            >
              Edit Intake
            </button>
          )}
          <button
            type="button"
            className={styles.exportBtn}
            onClick={handleExport}
            aria-label="Export intake as PDF"
          >
            Export PDF
          </button>
        </div>
      </div>

      {/* Chief Complaint */}
      <section className={styles.section} aria-labelledby="cc-heading">
        <h3 id="cc-heading" className={styles.sectionHeading}>Chief Complaint</h3>
        {intake.chiefComplaint
          ? <p className={styles.complaint}>{intake.chiefComplaint}</p>
          : <p className={styles.none}>Not provided</p>}
      </section>

      {/* Medical History */}
      <section className={styles.section} aria-labelledby="history-heading">
        <h3 id="history-heading" className={styles.sectionHeading}>Medical History</h3>
        {intake.medicalHistory.length === 0
          ? <p className={styles.none}>None reported</p>
          : (
            <ul className={styles.conditionList}>
              {intake.medicalHistory.map((h, i) => (
                <li key={i} className={styles.conditionRow}>
                  <span className={styles.conditionName}>{h.conditionName}</span>
                  {h.conditionCode && <code className={styles.code}>{h.conditionCode}</code>}
                  <span className={`${styles.statusTag} ${h.conditionStatus === 'active' ? styles.statusActive : styles.statusInactive}`}>
                    {h.conditionStatus}
                  </span>
                  <ConfidencePill score={h.confidenceScore} />
                </li>
              ))}
            </ul>
          )}
      </section>

      {/* Medications */}
      <section className={styles.section} aria-labelledby="meds-heading">
        <h3 id="meds-heading" className={styles.sectionHeading}>Medications</h3>
        {intake.medications.length === 0
          ? <p className={styles.none}>None reported</p>
          : (
            <div className={styles.tableWrapper}>
              <table className={styles.table} aria-label="Medications">
                <thead>
                  <tr>
                    <th scope="col" className={styles.th}>Medication</th>
                    <th scope="col" className={styles.th}>Dosage</th>
                    <th scope="col" className={styles.th}>Frequency</th>
                    <th scope="col" className={styles.th}>Route</th>
                  </tr>
                </thead>
                <tbody>
                  {intake.medications.map((m, i) => (
                    <tr key={i}>
                      <td className={styles.td}>
                        {m.medicationName}
                        <ConfidencePill score={m.confidenceScore} />
                      </td>
                      <td className={styles.td}>{m.dosage ?? '—'}</td>
                      <td className={styles.td}>{m.frequency ?? '—'}</td>
                      <td className={styles.td}>{m.route ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </section>

      {/* Allergies */}
      <section className={styles.section} aria-labelledby="allergies-heading">
        <h3 id="allergies-heading" className={styles.sectionHeading}>Allergies</h3>
        {intake.allergies.length === 0
          ? <p className={styles.none}>None reported</p>
          : (
            <ul className={styles.allergyList}>
              {intake.allergies.map((a, i) => (
                <li key={i} className={styles.allergyRow}>
                  <div className={styles.allergyMain}>
                    <strong>{a.allergenName}</strong>
                    <span className={styles.allergyType}>{a.allergenType}</span>
                    <span className={`${styles.reactionTag} ${a.reactionType === 'allergic' ? styles.reactionAllergic : styles.reactionSide}`}>
                      {a.reactionType === 'allergic' ? 'Drug Allergy' : 'Side Effect'}
                    </span>
                    {a.severity && (
                      <span className={`${styles.severityTag} ${styles[`severity_${a.severity}`] ?? ''}`}>
                        {a.severity}
                      </span>
                    )}
                    <ConfidencePill score={a.confidenceScore} />
                  </div>
                  {a.reactionDescription && (
                    <p className={styles.allergyDesc}>{a.reactionDescription}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
      </section>

      {/* Insurance */}
      <section className={styles.section} aria-labelledby="insurance-heading">
        <h3 id="insurance-heading" className={styles.sectionHeading}>Insurance</h3>
        {!intake.insurance
          ? <p className={styles.none}>Not provided</p>
          : (
            <dl className={styles.insuranceGrid}>
              <dt>Plan</dt>
              <dd>{intake.insurance.insuranceName ?? '—'}</dd>
              <dt>Member ID</dt>
              <dd><code>{intake.insurance.memberId ?? '—'}</code></dd>
              {intake.insurance.groupNumber && (
                <>
                  <dt>Group</dt>
                  <dd>{intake.insurance.groupNumber}</dd>
                </>
              )}
              {intake.insurance.planName && (
                <>
                  <dt>Plan Type</dt>
                  <dd>{intake.insurance.planName}</dd>
                </>
              )}
              <dt>Status</dt>
              <dd><VerificationBadge status={intake.insurance.verificationStatus} /></dd>
            </dl>
          )}
      </section>
    </article>
  );
}
