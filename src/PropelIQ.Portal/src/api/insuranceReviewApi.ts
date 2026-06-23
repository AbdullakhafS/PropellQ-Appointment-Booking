import axios from 'axios';
import type {
  PendingInsuranceResponse,
  PendingQuery,
  VerifyInsuranceRequest,
  VerifyInsuranceResponse,
  BatchVerifyRequest,
  BatchVerifyResponse,
  AuditEntry,
} from '../types/insuranceReview';

const api = axios.create({ baseURL: '/api/insurance' });

export const insuranceReviewApi = {
  getPending: async (query: PendingQuery = {}): Promise<PendingInsuranceResponse> => {
    const { data } = await api.get<{ data: PendingInsuranceResponse }>('/pending', { params: query });
    return data.data;
  },

  verify: async (id: number, req: VerifyInsuranceRequest): Promise<VerifyInsuranceResponse> => {
    const { data } = await api.patch<{ data: VerifyInsuranceResponse }>(`/${id}/verify`, req);
    return data.data;
  },

  verifyBatch: async (req: BatchVerifyRequest): Promise<BatchVerifyResponse> => {
    const { data } = await api.patch<{ data: BatchVerifyResponse }>('/verify/batch', req);
    return data.data;
  },

  getAuditHistory: async (id: number): Promise<AuditEntry[]> => {
    const { data } = await api.get<{ data: AuditEntry[] }>(`/${id}/audit`);
    return data.data;
  },
};
