import React, { useState, useRef } from 'react';
import styles from './ChatInput.module.css';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
  onSwitchToManual: () => void;
  suggestManualFallback: boolean;
}

export function ChatInput({ onSend, disabled, onSwitchToManual, suggestManualFallback }: ChatInputProps) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className={styles.inputArea}>
      {suggestManualFallback && (
        <div className={styles.fallbackBanner} role="alert">
          <p>Having trouble? You can switch to the standard intake form.</p>
          <button
            type="button"
            className={styles.fallbackBtn}
            onClick={onSwitchToManual}
          >
            Switch to Manual Form
          </button>
        </div>
      )}
      <form onSubmit={handleSubmit} className={styles.form} noValidate>
        <label htmlFor="chat-input" className={styles.srOnly}>
          Type your response
        </label>
        <textarea
          id="chat-input"
          ref={textareaRef}
          className={styles.textarea}
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your response…"
          rows={2}
          disabled={disabled}
          aria-disabled={disabled}
          aria-label="Type your response"
          autoComplete="off"
        />
        <button
          type="submit"
          className={styles.sendBtn}
          disabled={disabled || !text.trim()}
          aria-label="Send message"
        >
          Send
        </button>
      </form>
      <p className={styles.hint}>Press Enter to send · Shift+Enter for new line</p>
    </div>
  );
}
