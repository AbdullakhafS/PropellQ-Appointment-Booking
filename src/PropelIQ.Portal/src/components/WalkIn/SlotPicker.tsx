import React, { useEffect } from 'react';
import { useSlotAvailability } from '../../hooks/useSlotAvailability';
import type { AvailableSlot, SelectedSlot, SlotQuery } from '../../types/slot';
import styles from './SlotPicker.module.css';

interface SlotPickerProps {
  query: SlotQuery;
  selectedSlot: SelectedSlot | null;
  onSelect: (slot: SelectedSlot) => void;
  onClearSelection: () => void;
  conflictError?: string | null;
}

export function SlotPicker({
  query,
  selectedSlot,
  onSelect,
  onClearSelection,
  conflictError,
}: SlotPickerProps) {
  const { slots, loadState, errorMsg, reload } = useSlotAvailability();

  useEffect(() => {
    reload(query);
  }, [query.providerId, query.clinicId, query.windowHours]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelect = (slot: AvailableSlot) => {
    onSelect({
      slotId: slot.slotId,
      version: slot.version,
      providerName: slot.providerName,
      startTime: slot.startTime,
      endTime: slot.endTime,
      durationMinutes: slot.durationMinutes,
    });
  };

  const formatTime = (iso: string) =>
    new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });

  return (
    <section className={styles.container} aria-labelledby="slot-picker-heading">
      <div className={styles.header}>
        <h3 id="slot-picker-heading" className={styles.heading}>
          Available Slots
        </h3>
        <button
          type="button"
          className={styles.refreshBtn}
          onClick={() => reload(query)}
          aria-label="Refresh available slots"
          disabled={loadState === 'loading'}
        >
          {loadState === 'loading' ? '…' : '↻'}
        </button>
      </div>

      {/* Conflict error banner */}
      {conflictError && (
        <div className={styles.conflictBanner} role="alert">
          <span>⚠ {conflictError}</span>
          <button
            type="button"
            className={styles.reloadConflictBtn}
            onClick={() => { onClearSelection(); reload(query); }}
          >
            Reload slots
          </button>
        </div>
      )}

      {loadState === 'loading' && (
        <div className={styles.loadingMsg} role="status" aria-live="polite">
          <div className={styles.spinner} aria-hidden="true" />
          Loading slots…
        </div>
      )}

      {(loadState === 'error') && (
        <div className={styles.errorState} role="alert">
          <p>{errorMsg}</p>
          <button
            type="button"
            className={styles.retryBtn}
            onClick={() => reload(query)}
          >
            Retry
          </button>
        </div>
      )}

      {loadState === 'loaded' && slots.length === 0 && (
        <NoSlotFallback onChangeCriteria={onClearSelection} onRetry={() => reload(query)} />
      )}

      {loadState === 'loaded' && slots.length > 0 && (
        <ul
          className={styles.slotList}
          role="listbox"
          aria-label="Available appointment slots"
        >
          {slots.map(slot => {
            const isSelected = selectedSlot?.slotId === slot.slotId;
            return (
              <li
                key={slot.slotId}
                className={`${styles.slotRow} ${isSelected ? styles.slotSelected : ''}`}
                role="option"
                aria-selected={isSelected}
                onClick={() => handleSelect(slot)}
                onKeyDown={e => {
                  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSelect(slot); }
                }}
                tabIndex={0}
              >
                <div className={styles.slotMain}>
                  <span className={styles.providerName}>{slot.providerName}</span>
                  <span className={styles.slotTime}>
                    {formatDate(slot.startTime)} &bull; {formatTime(slot.startTime)} – {formatTime(slot.endTime)}
                  </span>
                </div>
                <div className={styles.slotMeta}>
                  {slot.durationMinutes} min
                  {slot.location && ` · ${slot.location}`}
                </div>
                {isSelected && (
                  <span className={styles.selectedBadge} aria-label="Selected">✓</span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

// --- No-slot fallback (task_032_004) ---

interface NoSlotFallbackProps {
  onChangeCriteria: () => void;
  onRetry: () => void;
}

function NoSlotFallback({ onChangeCriteria, onRetry }: NoSlotFallbackProps) {
  return (
    <div className={styles.noSlot} role="status" aria-live="polite">
      <p className={styles.noSlotIcon} aria-hidden="true">📅</p>
      <p className={styles.noSlotTitle}>No slots available</p>
      <p className={styles.noSlotSubtitle}>
        This provider is fully booked for the selected window.
      </p>
      <div className={styles.noSlotActions}>
        <button
          type="button"
          className={styles.alternativeBtn}
          onClick={onChangeCriteria}
          aria-label="Try a different provider or clinic"
        >
          Try another provider
        </button>
        <button
          type="button"
          className={styles.retryBtn}
          onClick={onRetry}
          aria-label="Refresh availability"
        >
          Refresh
        </button>
      </div>
    </div>
  );
}
