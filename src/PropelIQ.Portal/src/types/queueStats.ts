export type WaitHealth = 'Normal' | 'Warning' | 'Critical';

export interface QueueStats {
  activePatientCount: number;
  walkInCount: number;
  arrivedCount: number;
  averageWaitMinutes: number;
  maxWaitMinutes: number;
  waitHealth: WaitHealth;
  waitWarningThreshold: number;   // minutes
  waitCriticalThreshold: number;  // minutes
  computedAt: string;
}
