import axios from 'axios';
import type { ProfileIntake, UpdateIntakePayload } from '../types/profileIntake';

const api = axios.create({ baseURL: '/api/patients' });

export const patientIntakeApi = {
  getLatest: async (patientId: number): Promise<ProfileIntake | null> => {
    const { status, data } = await api.get<{ data: ProfileIntake }>(
      `/${patientId}/intake/latest`,
      { validateStatus: s => s === 200 || s === 204 }
    );
    return status === 204 ? null : data.data;
  },

  update: async (
    patientId: number,
    intakeId: number,
    payload: UpdateIntakePayload
  ): Promise<ProfileIntake> => {
    const { data } = await api.patch<{ data: ProfileIntake }>(
      `/${patientId}/intake/${intakeId}`,
      payload
    );
    return data.data;
  },
};
