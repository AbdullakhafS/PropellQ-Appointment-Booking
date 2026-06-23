export interface AppointmentHistoryEntry {
  id: string;
  previousStatus: string;
  newStatus: string;
  transitionedAtUtc: string;
  notes: string | null;
}

export interface AppointmentDetail {
  appointmentId: string;
  patientId: string;
  patientFullName: string;
  providerName: string;
  appointmentTime: string;
  durationMinutes: number;
  isWalkIn: boolean;
  status: string;
  createdAt: string;
  arrivedAt: string | null;
  statusHistory: AppointmentHistoryEntry[];
}
