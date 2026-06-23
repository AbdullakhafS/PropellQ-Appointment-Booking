import axios from 'axios';
import type { AvailableSlot, SlotQuery } from '../types/slot';

const api = axios.create({ baseURL: '/api/walk-in/slots' });

function unwrap<T>(response: { data: { data: T } }): T {
  return response.data.data;
}

export const slotApi = {
  getAvailableSlots: async (query: SlotQuery = {}): Promise<AvailableSlot[]> => {
    const response = await api.get('', { params: query });
    return unwrap<AvailableSlot[]>(response);
  },
};
