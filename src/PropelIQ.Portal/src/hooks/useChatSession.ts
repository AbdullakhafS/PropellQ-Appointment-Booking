import { useState, useCallback, useRef } from 'react';
import { chatApi } from '../api/chatApi';
import type { Message, ExtractedData, ConfidenceScores } from '../types/chat';

export type ChatStatus = 'idle' | 'loading' | 'active' | 'complete' | 'error';

interface ChatState {
  conversationId: number | null;
  messages: Message[];
  extractedData: ExtractedData | null;
  confidenceScores: ConfidenceScores | null;
  status: ChatStatus;
  error: string | null;
  suggestManualFallback: boolean;
  isComplete: boolean;
  currentStage: number;
  totalStages: number;
}

export function useChatSession(appointmentId: number, patientId: number, patientName: string) {
  const [state, setState] = useState<ChatState>({
    conversationId: null,
    messages: [],
    extractedData: null,
    confidenceScores: null,
    status: 'idle',
    error: null,
    suggestManualFallback: false,
    isComplete: false,
    currentStage: 0,
    totalStages: 6,
  });

  const retryCountRef = useRef(0);

  const startSession = useCallback(async () => {
    setState(prev => ({ ...prev, status: 'loading', error: null }));
    try {
      const result = await chatApi.startSession({ appointmentId, patientId, patientName });
      const welcomeMsg: Message = {
        role: 'assistant',
        content: result.welcomeMessage,
        timestamp: new Date().toISOString(),
      };
      setState(prev => ({
        ...prev,
        conversationId: result.conversationId,
        messages: [welcomeMsg],
        status: 'active',
        currentStage: result.currentStage,
        totalStages: result.totalStages,
      }));
    } catch {
      setState(prev => ({
        ...prev,
        status: 'error',
        error: 'Failed to start the intake session. Please try again.',
      }));
    }
  }, [appointmentId, patientId, patientName]);

  const sendMessage = useCallback(async (userText: string) => {
    if (!state.conversationId) return;

    const userMsg: Message = {
      role: 'user',
      content: userText,
      timestamp: new Date().toISOString(),
    };

    setState(prev => ({
      ...prev,
      messages: [...prev.messages, userMsg],
      status: 'loading',
    }));

    try {
      const result = await chatApi.sendMessage({
        conversationId: state.conversationId,
        appointmentId,
        userMessage: userText,
      });

      const assistantMsg: Message = {
        role: 'assistant',
        content: result.assistantMessage,
        timestamp: new Date().toISOString(),
      };

      retryCountRef.current = 0;

      setState(prev => ({
        ...prev,
        messages: [...prev.messages, assistantMsg],
        extractedData: result.extractedData,
        confidenceScores: result.confidenceScores,
        status: result.isComplete ? 'complete' : 'active',
        isComplete: result.isComplete,
        suggestManualFallback: result.suggestManualFallback,
        currentStage: result.currentStage,
        totalStages: result.totalStages,
      }));
    } catch {
      retryCountRef.current += 1;
      setState(prev => ({
        ...prev,
        status: 'active',
        error: 'Message failed to send. Please try again.',
      }));
    }
  }, [state.conversationId, appointmentId]);

  const dismissError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  return { ...state, startSession, sendMessage, dismissError };
}
