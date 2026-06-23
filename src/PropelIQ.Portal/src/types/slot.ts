export interface AvailableSlot {
  slotId: string;
  version: number;
  providerId: string;
  providerName: string;
  startTime: string;
  endTime: string;
  durationMinutes: number;
  location: string | null;
}

export interface SlotQuery {
  providerId?: string;
  clinicId?: string;
  windowHours?: number;
}

export interface SelectedSlot {
  slotId: string;
  version: number;
  providerName: string;
  startTime: string;
  endTime: string;
  durationMinutes: number;
}

export type SlotLoadState = 'idle' | 'loading' | 'loaded' | 'error';
