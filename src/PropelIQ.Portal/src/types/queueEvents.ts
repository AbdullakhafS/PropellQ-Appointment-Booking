import type { QueueAppointment } from './queue';

export type QueueEventType = 'queue.added' | 'queue.updated' | 'queue.removed';

export interface QueueEventPayload {
  eventType: 'Added' | 'Updated' | 'Removed';
  appointmentId: string;
  patientId: string;
  patientFullName: string;
  providerName: string;
  appointmentTime: string;
  durationMinutes: number;
  isWalkIn: boolean;
  status: string;
  occurredAt: string;
  arrivedAt?: string | null;
}

export type SseConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

/** Converts an SSE queue event payload into the UI's QueueAppointment shape. */
export function eventToQueueAppointment(evt: QueueEventPayload): QueueAppointment {
  return {
    appointmentId: evt.appointmentId,
    patientId: evt.patientId,
    patientFullName: evt.patientFullName,
    providerName: evt.providerName,
    appointmentTime: evt.appointmentTime,
    durationMinutes: evt.durationMinutes,
    isWalkIn: evt.isWalkIn,
    slotId: null,
    status: evt.status as QueueAppointment['status'],
    createdAt: evt.occurredAt,
    position: 0,
    arrivedAt: evt.arrivedAt ?? null,
  };
}
