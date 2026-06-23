import axios from 'axios';
import type { AppointmentDetail, AppointmentHistoryEntry } from '../types/appointmentDetail';

const api = axios.create({ baseURL: '/api/appointments' });

function unwrap<T>(response: { data: { data: T } }): T {
  return response.data.data;
}

export const appointmentApi = {
  getDetail: async (appointmentId: string): Promise<AppointmentDetail> => {
    const response = await api.get<{ data: AppointmentDetail }>(`/${appointmentId}`);
    return unwrap(response);
  },

  getHistory: async (appointmentId: string): Promise<AppointmentHistoryEntry[]> => {
    const response = await api.get<{ data: AppointmentHistoryEntry[] }>(`/${appointmentId}/history`);
    return unwrap(response);
  },
};
