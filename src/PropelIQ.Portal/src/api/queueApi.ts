import axios from 'axios';
import type {
  QueueResponse,
  QueueFilter,
  QueueAppointment,
  RescheduleRequest,
  ReorderQueueRequest,
  ReorderQueueResponse,
  CheckInResult,
  CancelAppointmentResult,
} from '../types/queue';

const api = axios.create({ baseURL: '/api/queue' });

function unwrap<T>(response: { data: { data: T } }): T {
  return response.data.data;
}

export const queueApi = {
  getQueue: async (filter: QueueFilter = {}): Promise<QueueResponse> => {
    const response = await api.get('', { params: filter });
    return unwrap<QueueResponse>(response);
  },

  reschedule: async (
    appointmentId: string,
    request: RescheduleRequest
  ): Promise<QueueAppointment> => {
    const response = await api.patch(`/${appointmentId}/reschedule`, request);
    return unwrap<QueueAppointment>(response);
  },

  reorder: async (request: ReorderQueueRequest): Promise<ReorderQueueResponse> => {
    const response = await api.patch('/reorder', request);
    return unwrap<ReorderQueueResponse>(response);
  },

  checkIn: async (appointmentId: string): Promise<CheckInResult> => {
    const response = await api.patch(`/${appointmentId}/check-in`);
    return unwrap<CheckInResult>(response);
  },

  cancelAppointment: async (
    appointmentId: string,
    reason?: string
  ): Promise<CancelAppointmentResult> => {
    const response = await api.patch(`/${appointmentId}/cancel`, { reason: reason ?? null });
    return unwrap<CancelAppointmentResult>(response);
  },
};
