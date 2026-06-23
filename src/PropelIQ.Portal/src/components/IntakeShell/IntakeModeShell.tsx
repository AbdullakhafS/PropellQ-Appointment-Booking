import React, { useState, useCallback, useRef } from 'react';
import { ChatbotScreen } from '../ChatBot/ChatbotScreen';
import { ManualIntakeForm } from '../ManualIntakeForm/ManualIntakeForm';
import { useIntakeDraft } from '../../hooks/useIntakeDraft';
import { mapExtractedToForm, mapFormToExtracted, buildFormSummaryForChatbot } from '../../utils/intakeMapping';
import type { ExtractedData } from '../../types/chat';
import type { ManualIntakeFormData } from '../../types/intake';
import type { IntakeMode } from '../../types/draft';
import { MAX_SWITCHES } from '../../types/draft';
import styles from './IntakeModeShell.module.css';

interface IntakeModeShellProps {
  appointmentId: number;
  patientId: number;
  patientName: string;
  onIntakeComplete: () => void;
}

// Minimal EMPTY_FORM constant (same shape as ManualIntakeForm)
const EMPTY_FORM: ManualIntakeFormData = {
  chiefComplaint: '',
  medicalHistory: [],
  otherConditions: '',
  medications: [],
  allergies: [],
  insuranceInfo: { provider: '', memberId: '', groupNumber: '', planName: '' },
};

export function IntakeModeShell({
  appointmentId,
  patientId,
  patientName,
  onIntakeComplete,
}: IntakeModeShellProps) {
  const [hasChosen, setHasChosen] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [switchSuccess, setSwitchSuccess] = useState(false);

  // Captured data that survives mode switch
  const capturedExtractedRef = useRef<ExtractedData | null>(null);
  const capturedFormRef = useRef<ManualIntakeFormData>(EMPTY_FORM);

  // Pre-populated form data when switching AI → form
  const [formSeed, setFormSeed] = useState<Partial<ManualIntakeFormData>>({});
  // Summary injected into chatbot when switching form → AI
  const [chatbotContextNote, setChatbotContextNote] = useState<string>('');

  const { mode, switchCount, canSwitch, setMode, clearDraft } = useIntakeDraft(
    appointmentId,
    patientId,
    'ai'
  );

  const otherMode: IntakeMode = mode === 'ai' ? 'manual' : 'ai';
  const otherModeLabel = mode === 'ai' ? 'Fill Out Form' : 'Use AI Assistant';

  // ----- Initial mode selection -----
  const handleChooseMode = useCallback((chosen: IntakeMode) => {
    setMode(chosen, '{}');
    setHasChosen(true);
  }, [setMode]);

  // ----- Confirm switch -----
  const handleConfirmSwitch = useCallback(async () => {
    setShowConfirm(false);

    let dataJson = '{}';
    if (mode === 'ai' && capturedExtractedRef.current) {
      // AI → Manual: map extracted chatbot data → form fields
      const mapped = mapExtractedToForm(capturedExtractedRef.current);
      setFormSeed(mapped);
      dataJson = JSON.stringify(mapped);
    } else if (mode === 'manual') {
      // Manual → AI: build summary note for chatbot to contextualise
      const summary = buildFormSummaryForChatbot(capturedFormRef.current);
      setChatbotContextNote(summary);
      // Also persist mapped form data in case chatbot needs it
      const extracted = mapFormToExtracted(capturedFormRef.current);
      dataJson = JSON.stringify(extracted);
    }

    await setMode(otherMode, dataJson);
    setSwitchSuccess(true);
    setTimeout(() => setSwitchSuccess(false), 3000);
  }, [mode, otherMode, setMode]);

  // ----- Callbacks from child screens -----
  const handleChatbotDataUpdate = useCallback((extracted: ExtractedData) => {
    capturedExtractedRef.current = extracted;
  }, []);

  const handleFormDataUpdate = useCallback((formData: ManualIntakeFormData) => {
    capturedFormRef.current = formData;
  }, []);

  const handleSwitchToManual = useCallback(() => {
    // Called from ChatbotScreen's existing "Switch to Manual Form" button
    if (!canSwitch) return;
    if (capturedExtractedRef.current) {
      setFormSeed(mapExtractedToForm(capturedExtractedRef.current));
    }
    setMode('manual', JSON.stringify(capturedExtractedRef.current ?? {}));
    setSwitchSuccess(true);
    setTimeout(() => setSwitchSuccess(false), 3000);
  }, [canSwitch, setMode]);

  const handleIntakeComplete = useCallback(async () => {
    await clearDraft();
    onIntakeComplete();
  }, [clearDraft, onIntakeComplete]);

  // ----- Mode selection screen -----
  if (!hasChosen) {
    return (
      <div className={styles.modeSelect} role="main" aria-labelledby="mode-heading">
        <h1 id="mode-heading" className={styles.modeHeading}>How would you like to complete your intake?</h1>
        <p className={styles.modeSubtext}>Choose the method that works best for you. You can switch later.</p>
        <div className={styles.modeCards}>
          <button
            type="button"
            className={styles.modeCard}
            onClick={() => handleChooseMode('ai')}
            autoFocus
          >
            <span className={styles.modeIcon} aria-hidden="true">🤖</span>
            <span className={styles.modeCardTitle}>Use AI Assistant</span>
            <span className={styles.modeCardDesc}>Answer a few questions in a conversation. Takes about 5–7 minutes.</span>
          </button>
          <button
            type="button"
            className={styles.modeCard}
            onClick={() => handleChooseMode('manual')}
          >
            <span className={styles.modeIcon} aria-hidden="true">📋</span>
            <span className={styles.modeCardTitle}>Fill Out Form</span>
            <span className={styles.modeCardDesc}>Complete a structured form at your own pace.</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.shell}>
      {/* Switch toolbar */}
      <div className={styles.toolbar}>
        <span className={styles.modeTag}>
          {mode === 'ai' ? '🤖 AI Assistant' : '📋 Manual Form'}
        </span>
        <div className={styles.toolbarRight}>
          {switchSuccess && (
            <span className={styles.switchBanner} role="status" aria-live="polite">
              ✓ Switched — your responses were preserved
            </span>
          )}
          {canSwitch ? (
            <button
              type="button"
              className={styles.switchBtn}
              onClick={() => setShowConfirm(true)}
              aria-label={`Switch to ${otherModeLabel}`}
            >
              Switch to {otherModeLabel}
            </button>
          ) : (
            <span className={styles.switchDisabled} aria-label={`Switch limit reached (${MAX_SWITCHES} max)`}>
              Switch limit reached
            </span>
          )}
          {switchCount > 0 && canSwitch && (
            <span className={styles.switchRemaining}>
              {MAX_SWITCHES - switchCount} switch{MAX_SWITCHES - switchCount !== 1 ? 'es' : ''} remaining
            </span>
          )}
        </div>
      </div>

      {/* Active mode content */}
      <div className={styles.content}>
        {mode === 'ai' ? (
          <ChatbotScreen
            appointmentId={appointmentId}
            patientId={patientId}
            patientName={patientName}
            onSwitchToManual={handleSwitchToManual}
            onIntakeComplete={handleIntakeComplete}
            onExtractedDataChange={handleChatbotDataUpdate}
          />
        ) : (
          <ManualIntakeForm
            appointmentId={appointmentId}
            patientId={patientId}
            seed={formSeed}
            onFormChange={handleFormDataUpdate}
            onSubmitSuccess={handleIntakeComplete}
          />
        )}
      </div>

      {/* Confirmation modal */}
      {showConfirm && (
        <div
          className={styles.overlay}
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-heading"
        >
          <div className={styles.modal}>
            <h2 id="confirm-heading" className={styles.modalHeading}>
              Switch to {otherModeLabel}?
            </h2>
            <p className={styles.modalBody}>Your responses will be preserved and pre-filled in the other mode.</p>
            <div className={styles.modalActions}>
              <button
                type="button"
                className={styles.confirmYes}
                onClick={handleConfirmSwitch}
                autoFocus
              >
                Yes, Switch
              </button>
              <button
                type="button"
                className={styles.confirmNo}
                onClick={() => setShowConfirm(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
