import axios from 'axios';
import type { IntakeDraftData } from '../types/draft';

const api = axios.create({ baseURL: '/api/intake' });

export const draftApi = {
  getDraft: async (appointmentId: number): Promise<IntakeDraftData | null> => {
    const { status, data } = await api.get<{ data: IntakeDraftData }>(
      `/${appointmentId}/draft`,
      { validateStatus: s => s === 200 || s === 204 }
    );
    return status === 204 ? null : data.data;
  },

  saveDraft: async (
    appointmentId: number,
    patientId: number,
    mode: string,
    dataJson: string,
    switchCount: number
  ): Promise<void> => {
    await api.post(`/${appointmentId}/draft`, { patientId, mode, dataJson, switchCount });
  },

  deleteDraft: async (appointmentId: number): Promise<void> => {
    await api.delete(`/${appointmentId}/draft`);
  },
};
