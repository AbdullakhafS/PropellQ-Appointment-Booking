import { useState, useCallback, useEffect } from 'react';
import { draftApi } from '../api/draftApi';
import type { IntakeMode, LocalDraftState } from '../types/draft';
import { MAX_SWITCHES } from '../types/draft';

const DRAFT_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

function storageKey(appointmentId: number): string {
  return `intake_draft_${appointmentId}`;
}

function readLocal(appointmentId: number): LocalDraftState | null {
  try {
    const raw = localStorage.getItem(storageKey(appointmentId));
    if (!raw) return null;
    const parsed: LocalDraftState = JSON.parse(raw);
    if (Date.now() - parsed.savedAt > DRAFT_TTL_MS) {
      localStorage.removeItem(storageKey(appointmentId));
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function writeLocal(state: LocalDraftState): void {
  try {
    localStorage.setItem(storageKey(state.appointmentId), JSON.stringify(state));
  } catch {
    // Storage quota exceeded — non-fatal
  }
}

function clearLocal(appointmentId: number): void {
  try {
    localStorage.removeItem(storageKey(appointmentId));
  } catch { /* noop */ }
}

interface UseIntakeDraftReturn {
  mode: IntakeMode;
  switchCount: number;
  canSwitch: boolean;
  setMode: (newMode: IntakeMode, dataJson?: string) => Promise<void>;
  clearDraft: () => Promise<void>;
}

export function useIntakeDraft(
  appointmentId: number,
  patientId: number,
  initialMode: IntakeMode = 'ai'
): UseIntakeDraftReturn {
  const [mode, setModeState] = useState<IntakeMode>(initialMode);
  const [switchCount, setSwitchCount] = useState(0);

  // Restore from localStorage on mount
  useEffect(() => {
    const local = readLocal(appointmentId);
    if (local && local.patientId === patientId) {
      setModeState(local.mode);
      setSwitchCount(local.switchCount);
    }
  }, [appointmentId, patientId]);

  const setMode = useCallback(async (newMode: IntakeMode, dataJson = '{}') => {
    const nextCount = switchCount + 1;
    setSwitchCount(nextCount);
    setModeState(newMode);

    const local: LocalDraftState = {
      appointmentId,
      patientId,
      mode: newMode,
      switchCount: nextCount,
      savedAt: Date.now(),
    };
    writeLocal(local);

    // Best-effort backend persist — do not block the UI
    draftApi
      .saveDraft(appointmentId, patientId, newMode, dataJson, nextCount)
      .catch(() => { /* silent — user still gets the mode switch */ });
  }, [appointmentId, patientId, switchCount]);

  const clearDraft = useCallback(async () => {
    clearLocal(appointmentId);
    await draftApi.deleteDraft(appointmentId).catch(() => { /* silent */ });
  }, [appointmentId]);

  return {
    mode,
    switchCount,
    canSwitch: switchCount < MAX_SWITCHES,
    setMode,
    clearDraft,
  };
}
