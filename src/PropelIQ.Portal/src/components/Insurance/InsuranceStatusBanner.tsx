import type { InsurancePreCheckResult } from '../../types/insurance';
import styles from './InsuranceStatusBanner.module.css';

interface InsuranceStatusBannerProps {
  result: InsurancePreCheckResult;
}

export function InsuranceStatusBanner({ result }: InsuranceStatusBannerProps) {
  if (result.isVerified) {
    return (
      <div className={styles.verified} role="status" aria-live="polite">
        <span className={styles.icon} aria-hidden="true">✓</span>
        <span>
          Insurance verified
          {result.matchedPlanName && ` — ${result.matchedPlanName}`}
          {` (${result.confidenceScore}% confidence)`}.
        </span>
      </div>
    );
  }

  return (
    <div className={styles.unverified} role="alert" aria-live="assertive">
      <span className={styles.icon} aria-hidden="true">⚠</span>
      <span>
        We couldn't verify your insurance. Don't worry — you can still book.
        We'll verify it after your visit.
        {result.reason && <em className={styles.reason}> ({result.reason})</em>}
      </span>
    </div>
  );
}
