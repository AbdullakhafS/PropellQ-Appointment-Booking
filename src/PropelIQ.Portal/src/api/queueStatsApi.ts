import axios from 'axios';
import type { QueueStats } from '../types/queueStats';

const api = axios.create({ baseURL: '/api/queue' });

export const queueStatsApi = {
  getStats: async (): Promise<QueueStats> => {
    const { data } = await api.get<{ data: QueueStats }>('/stats');
    return data.data;
  },
};
