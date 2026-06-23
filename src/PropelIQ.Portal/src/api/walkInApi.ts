import axios from 'axios';
import type {
  PatientSummary,
  CreatePatientRequest,
  BookWalkInRequest,
  WalkInAppointment,
} from '../types/walkIn';

const api = axios.create({ baseURL: '/api/walk-in' });

function unwrap<T>(response: { data: { data: T } }): T {
  return response.data.data;
}

export const walkInApi = {
  searchPatients: async (term: string, limit = 20): Promise<PatientSummary[]> => {
    const response = await api.get('/patients/search', { params: { q: term, limit } });
    return unwrap<PatientSummary[]>(response);
  },

  createPatient: async (request: CreatePatientRequest): Promise<PatientSummary> => {
    const response = await api.post('/patients', request);
    return unwrap<PatientSummary>(response);
  },

  bookWalkIn: async (request: BookWalkInRequest): Promise<WalkInAppointment> => {
    const response = await api.post('/appointments', request);
    return unwrap<WalkInAppointment>(response);
  },
};
