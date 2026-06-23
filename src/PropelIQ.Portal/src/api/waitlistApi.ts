import axios from 'axios';
import type {
  WaitlistEntry,
  WaitlistOffer,
  JoinWaitlistRequest,
  IssueOfferRequest,
  OfferConversionResult,
} from '../types/waitlist';

const api = axios.create({ baseURL: '/api/waitlist' });

function unwrap<T>(response: { data: { data: T } }): T {
  return response.data.data;
}

export const waitlistApi = {
  getEntries: async (providerId?: string): Promise<WaitlistEntry[]> => {
    const response = await api.get('', { params: providerId ? { providerId } : {} });
    return unwrap<WaitlistEntry[]>(response);
  },

  join: async (request: JoinWaitlistRequest): Promise<WaitlistEntry> => {
    const response = await api.post('', request);
    return unwrap<WaitlistEntry>(response);
  },

  cancel: async (entryId: string): Promise<void> => {
    await api.delete(`/${entryId}`);
  },

  issueOffer: async (request: IssueOfferRequest): Promise<WaitlistOffer | null> => {
    const response = await api.post<{ data: WaitlistOffer } | null>('/offers/issue', request, {
      validateStatus: s => s === 201 || s === 204,
    });
    return response.status === 204 ? null : response.data?.data ?? null;
  },

  getPendingOffers: async (): Promise<WaitlistOffer[]> => {
    const response = await api.get('/offers/pending');
    return unwrap<WaitlistOffer[]>(response);
  },

  respond: async (offerId: string, isAccept: boolean): Promise<OfferConversionResult> => {
    const response = await api.patch(`/offers/${offerId}/respond`, { isAccept });
    return unwrap<OfferConversionResult>(response);
  },

  processExpired: async (): Promise<void> => {
    await api.post('/offers/process-expired');
  },
};
