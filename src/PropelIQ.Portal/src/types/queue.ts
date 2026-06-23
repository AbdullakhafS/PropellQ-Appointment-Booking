export type AppointmentStatus = 'scheduled' | 'arrived' | 'completed' | 'cancelled';

export interface QueueAppointment {
  appointmentId: string;
  patientId: string;
  patientFullName: string;
  providerName: string;
  appointmentTime: string;
  durationMinutes: number;
  isWalkIn: boolean;
  slotId: string | null;
  status: AppointmentStatus;
  createdAt: string;
  position: number;
  arrivedAt: string | null;
}

export interface QueueResponse {
  items: QueueAppointment[];
  totalCount: number;
  page: number;
  pageSize: number;
  hasWalkIns: boolean;
  version: number;
}

export interface QueueFilter {
  date?: string;
  status?: string;
  isWalkIn?: boolean;
  providerId?: string;
  page?: number;
  pageSize?: number;
}

export interface RescheduleRequest {
  newTime: string;
  durationMinutes?: number;
  notes?: string;
}

export interface CheckInResult {
  appointmentId: string;
  status: 'arrived';
  arrivedAt: string;
}

export interface ReorderQueueRequest {
  orderedAppointmentIds: string[];
  expectedVersion: number;
}

export interface ReorderQueueResponse {
  orderedIds: string[];
  newVersion: number;
}

export interface CancelAppointmentResult {
  appointmentId: string;
  status: 'cancelled';
}
