import styles from './ProgressIndicator.module.css';

const STAGE_LABELS: Readonly<Record<number, string>> = {
  1: 'Chief Complaint',
  2: 'Medical History',
  3: 'Medications',
  4: 'Allergies',
  5: 'Insurance',
  6: 'Summary',
};

interface ProgressIndicatorProps {
  currentStage: number;
  totalStages: number;
}

export function ProgressIndicator({ currentStage, totalStages }: ProgressIndicatorProps) {
  if (currentStage === 0) return null;

  const label = STAGE_LABELS[currentStage] ?? 'In Progress';
  const percentage = Math.round((currentStage / totalStages) * 100);

  return (
    <div
      className={styles.container}
      role="status"
      aria-label={`Step ${currentStage} of ${totalStages}: ${label}`}
    >
      <div className={styles.stepInfo}>
        <span className={styles.stepLabel}>{label}</span>
        <span className={styles.stepCounter} aria-hidden="true">
          Step {currentStage} of {totalStages}
        </span>
      </div>
      <div className={styles.track} aria-hidden="true">
        <div className={styles.fill} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}
