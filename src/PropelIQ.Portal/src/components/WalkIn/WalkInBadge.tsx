import styles from './WalkInBadge.module.css';

interface WalkInBadgeProps {
  /** Size variant — 'sm' for table rows, 'md' (default) for cards. */
  size?: 'sm' | 'md';
}

/**
 * Displays a consistent "Walk-In" label for walk-in appointments.
 * Should only be rendered when isWalkIn === true.
 */
export function WalkInBadge({ size = 'md' }: WalkInBadgeProps) {
  return (
    <span
      className={`${styles.badge} ${size === 'sm' ? styles.sm : ''}`}
      aria-label="Walk-in appointment"
      title="Walk-in appointment"
    >
      Walk-In
    </span>
  );
}
