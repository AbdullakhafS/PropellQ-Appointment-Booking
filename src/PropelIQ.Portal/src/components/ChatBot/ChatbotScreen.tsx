import { useEffect, useRef, useCallback } from 'react';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { IntakeSummary } from './IntakeSummary';
import { useChatSession } from '../../hooks/useChatSession';
import { chatApi } from '../../api/chatApi';
import styles from './ChatbotScreen.module.css';

interface ChatbotScreenProps {
  appointmentId: number;
  patientId: number;
  patientName: string;
  onSwitchToManual: () => void;
  onIntakeComplete: () => void;
}

export function ChatbotScreen({
  appointmentId,
  patientId,
  patientName,
  onSwitchToManual,
  onIntakeComplete,
}: ChatbotScreenProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  const {
    conversationId,
    messages,
    status,
    error,
    extractedData,
    suggestManualFallback,
    isComplete,
    startSession,
    sendMessage,
    dismissError,
  } = useChatSession(appointmentId, patientId, patientName);

  const isLoading = status === 'loading';

  useEffect(() => {
    startSession();
  }, [startSession]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleEdit = useCallback(() => {
    // Sends a request to continue editing — re-opens the chat
    sendMessage('I would like to review and correct my answers.');
  }, [sendMessage]);

  const handleSwitchToManual = useCallback(async () => {
    if (conversationId) {
      try {
        await chatApi.switchToManual(conversationId);
      } catch {
        // Best-effort: still switch UI even if the API call fails
      }
    }
    onSwitchToManual();
  }, [conversationId, onSwitchToManual]);

  if (isComplete && extractedData) {
    return (
      <div className={styles.screen}>
        <IntakeSummary
          data={extractedData}
          onConfirm={onIntakeComplete}
          onEdit={handleEdit}
        />
      </div>
    );
  }

  return (
    <div className={styles.screen} role="main">
      <header className={styles.header}>
        <h1 className={styles.title}>AI Intake Assistant</h1>
        <button
          type="button"
          className={styles.manualBtn}
          onClick={handleSwitchToManual}
          aria-label="Switch to manual intake form"
        >
          Switch to Manual Form
        </button>
      </header>

      {error && (
        <div className={styles.errorBanner} role="alert">
          <span>{error}</span>
          <button type="button" className={styles.dismissBtn} onClick={dismissError} aria-label="Dismiss error">
            ✕
          </button>
        </div>
      )}

      {status === 'idle' || (status === 'loading' && messages.length === 0) ? (
        <div className={styles.startingIndicator} role="status" aria-live="polite">
          <div className={styles.spinner} aria-hidden="true" />
          <p>Starting your intake session…</p>
        </div>
      ) : (
        <MessageList
          messages={messages}
          isLoading={isLoading}
          ref={bottomRef}
        />
      )}

      <ChatInput
        onSend={sendMessage}
        disabled={isLoading || status === 'idle' || status === 'error'}
        onSwitchToManual={handleSwitchToManual}
        suggestManualFallback={suggestManualFallback}
      />
    </div>
  );
}
