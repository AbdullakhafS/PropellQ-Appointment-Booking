import axios from 'axios';
import type {
  StartChatRequest,
  StartChatResponse,
  SendMessageRequest,
  SendMessageResponse,
  ConversationHistoryResponse,
} from '../types/chat';

const api = axios.create({ baseURL: '/api/intake/chat' });

export const chatApi = {
  startSession: async (req: StartChatRequest): Promise<StartChatResponse> => {
    const { data } = await api.post<{ data: StartChatResponse }>('/start', req);
    return data.data;
  },

  sendMessage: async (req: SendMessageRequest): Promise<SendMessageResponse> => {
    const { data } = await api.post<{ data: SendMessageResponse }>('/message', req);
    return data.data;
  },

  getHistory: async (conversationId: number): Promise<ConversationHistoryResponse> => {
    const { data } = await api.get<{ data: ConversationHistoryResponse }>(`/${conversationId}`);
    return data.data;
  },

  switchToManual: async (conversationId: number): Promise<void> => {
    await api.post(`/${conversationId}/switch-to-manual`);
  },
};
