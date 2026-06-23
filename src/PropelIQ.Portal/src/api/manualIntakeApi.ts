import axios from 'axios';
import type {
  LastIntakeResponse,
  SubmitManualIntakeRequest,
  SubmitManualIntakeResponse,
} from '../types/intake';

const patientsApi = axios.create({ baseURL: '/api/patients' });
const intakeApi = axios.create({ baseURL: '/api/intake' });

export const manualIntakeApi = {
  getLastIntake: async (patientId: number): Promise<LastIntakeResponse | null> => {
    const { status, data } = await patientsApi.get<{ data: LastIntakeResponse }>(
      `/${patientId}/intake/last`,
      { validateStatus: s => s === 200 || s === 204 }
    );
    return status === 204 ? null : data.data;
  },

  submit: async (req: SubmitManualIntakeRequest): Promise<SubmitManualIntakeResponse> => {
    const { data } = await intakeApi.post<{ data: SubmitManualIntakeResponse }>('/submit', req);
    return data.data;
  },
};
