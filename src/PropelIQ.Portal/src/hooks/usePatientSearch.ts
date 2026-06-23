import { useState, useEffect, useRef, useCallback } from 'react';
import { walkInApi } from '../api/walkInApi';
import type { PatientSummary } from '../types/walkIn';

const DEBOUNCE_MS = 300;
const MIN_LENGTH = 2;

interface UsePatientSearchReturn {
  term: string;
  setTerm: (v: string) => void;
  results: PatientSummary[];
  isSearching: boolean;
  error: string | null;
  reset: () => void;
}

export function usePatientSearch(): UsePatientSearchReturn {
  const [term, setTerm] = useState('');
  const [results, setResults] = useState<PatientSummary[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = useCallback(async (q: string) => {
    setIsSearching(true);
    setError(null);
    try {
      const data = await walkInApi.searchPatients(q);
      setResults(data);
    } catch {
      setError('Patient search failed. Please try again.');
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (term.trim().length < MIN_LENGTH) {
      setResults([]);
      return;
    }
    timerRef.current = setTimeout(() => search(term), DEBOUNCE_MS);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [term, search]);

  const reset = useCallback(() => {
    setTerm('');
    setResults([]);
    setError(null);
  }, []);

  return { term, setTerm, results, isSearching, error, reset };
}
