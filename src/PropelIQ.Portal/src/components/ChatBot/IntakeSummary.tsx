import type { ExtractedData } from '../../types/chat';
import styles from './IntakeSummary.module.css';

interface IntakeSummaryProps {
  data: ExtractedData;
  onConfirm: () => void;
  onEdit: () => void;
}

export function IntakeSummary({ data, onConfirm, onEdit }: IntakeSummaryProps) {
  return (
    <section className={styles.summary} aria-labelledby="summary-heading">
      <h2 id="summary-heading" className={styles.heading}>Intake Summary</h2>
      <p className={styles.subtext}>
        Please review the information captured. You can confirm or go back to make corrections.
      </p>

      <dl className={styles.dataList}>
        <dt>Chief Complaint</dt>
        <dd>{data.chiefComplaint ?? <em>Not provided</em>}</dd>

        <dt>Medical History</dt>
        <dd>
          {data.medicalHistory.length > 0
            ? <ul className={styles.list}>{data.medicalHistory.map((h, i) => <li key={i}>{h}</li>)}</ul>
            : <em>None reported</em>}
        </dd>

        <dt>Medications</dt>
        <dd>
          {data.medications.length > 0
            ? (
              <ul className={styles.list}>
                {data.medications.map((m, i) => (
                  <li key={i}>
                    <strong>{m.name}</strong>
                    {m.dosage && ` — ${m.dosage}`}
                    {m.frequency && ` (${m.frequency})`}
                  </li>
                ))}
              </ul>
            )
            : <em>None reported</em>}
        </dd>

        <dt>Allergies</dt>
        <dd>
          {data.allergies.length > 0
            ? (
              <ul className={styles.list}>
                {data.allergies.map((a, i) => (
                  <li key={i}>
                    <strong>{a.allergen}</strong>
                    {a.reaction && ` — ${a.reaction}`}
                    <span className={styles.allergyType}>{a.type.replace('_', ' ')}</span>
                  </li>
                ))}
              </ul>
            )
            : <em>None reported</em>}
        </dd>

        <dt>Insurance</dt>
        <dd>
          {data.insuranceInfo
            ? (
              <address>
                {data.insuranceInfo.provider}<br />
                {data.insuranceInfo.memberId && <>Member ID: {data.insuranceInfo.memberId}<br /></>}
                {data.insuranceInfo.groupNumber && <>Group: {data.insuranceInfo.groupNumber}</>}
              </address>
            )
            : <em>Not provided</em>}
        </dd>
      </dl>

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.editBtn}
          onClick={onEdit}
          aria-label="Go back to edit intake information"
        >
          ← Edit Information
        </button>
        <button
          type="button"
          className={styles.confirmBtn}
          onClick={onConfirm}
          aria-label="Confirm and submit intake information"
        >
          Confirm & Submit
        </button>
      </div>
    </section>
  );
}
