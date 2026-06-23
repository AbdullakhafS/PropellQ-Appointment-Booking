export type IntakeMode = 'ai' | 'manual';

export const MAX_SWITCHES = 2;

export interface IntakeDraftData {
  mode: IntakeMode;
  dataJson: string;
  switchCount: number;
  lastUpdated: string;
  expiresAt: string;
}

/** Shape stored in localStorage alongside backend draft */
export interface LocalDraftState {
  appointmentId: number;
  patientId: number;
  mode: IntakeMode;
  switchCount: number;
  savedAt: number; // epoch ms
}
