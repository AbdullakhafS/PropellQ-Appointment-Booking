import React from 'react';
import type { Message } from '../../types/chat';
import styles from './MessageList.module.css';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
}

export const MessageList = React.forwardRef<HTMLDivElement, MessageListProps>(
  ({ messages, isLoading }, ref) => (
    <div className={styles.messageList} role="log" aria-live="polite" aria-label="Conversation">
      {messages
        .filter(m => m.role !== 'system')
        .map((msg, idx) => (
          <article
            key={idx}
            className={`${styles.bubble} ${msg.role === 'user' ? styles.user : styles.assistant}`}
            aria-label={msg.role === 'user' ? 'Your message' : 'Assistant message'}
          >
            <p className={styles.content}>{msg.content}</p>
            <time className={styles.timestamp} dateTime={msg.timestamp}>
              {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </time>
          </article>
        ))}
      {isLoading && (
        <div className={styles.typingIndicator} role="status" aria-label="Assistant is typing">
          <span />
          <span />
          <span />
        </div>
      )}
      <div ref={ref} />
    </div>
  )
);

MessageList.displayName = 'MessageList';
