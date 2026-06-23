// --- Patient ---

export interface PatientSummary {
  id: string;
  firstName: string;
  lastName: string;
  fullName: string;
  dateOfBirth: string;
  phone: string;
  email: string | null;
  gender: string;
}

export interface CreatePatientRequest {
  firstName: string;
  lastName: string;
  dateOfBirth: string;    // ISO date string "YYYY-MM-DD"
  phone: string;
  gender: string;
  email?: string;
  address?: string;
  notes?: string;
}

// --- Walk-in booking ---

export interface BookWalkInRequest {
  patientId: string;
  providerName: string;
  appointmentTime: string;  // ISO 8601 datetime
  durationMinutes: number;
  notes?: string;
  slotId?: string;
  slotVersion?: number;
}

export interface WalkInAppointment {
  appointmentId: string;
  patientId: string;
  patientFullName: string;
  providerName: string;
  appointmentTime: string;
  durationMinutes: number;
  isWalkIn: boolean;
  status: string;
  createdAt: string;
  slotId: string | null;
}

// --- Flow state ---

export type WalkInStep = 'search' | 'create' | 'book' | 'confirm';
