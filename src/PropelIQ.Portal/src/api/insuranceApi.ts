import axios from 'axios';
import type { InsurancePreCheckRequest, InsurancePreCheckResult } from '../types/insurance';

const api = axios.create({ baseURL: '/api/intake' });

export const insuranceApi = {
  check: async (req: InsurancePreCheckRequest): Promise<InsurancePreCheckResult> => {
    const { data } = await api.post<{ data: InsurancePreCheckResult }>('/insurance-check', req);
    return data.data;
  },
};
