import { useState, useCallback } from 'react';
import { slotApi } from '../api/slotApi';
import type { AvailableSlot, SlotQuery, SlotLoadState } from '../types/slot';

interface UseSlotAvailabilityReturn {
  slots: AvailableSlot[];
  loadState: SlotLoadState;
  errorMsg: string | null;
  reload: (query?: SlotQuery) => Promise<void>;
}

export function useSlotAvailability(): UseSlotAvailabilityReturn {
  const [slots, setSlots] = useState<AvailableSlot[]>([]);
  const [loadState, setLoadState] = useState<SlotLoadState>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const reload = useCallback(async (query: SlotQuery = {}) => {
    setLoadState('loading');
    setErrorMsg(null);
    try {
      const data = await slotApi.getAvailableSlots(query);
      setSlots(data);
      setLoadState('loaded');
    } catch {
      setErrorMsg('Failed to load available slots. Please try again.');
      setLoadState('error');
    }
  }, []);

  return { slots, loadState, errorMsg, reload };
}
