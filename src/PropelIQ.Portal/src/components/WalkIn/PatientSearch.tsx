import React, { useRef, useCallback } from 'react';
import { usePatientSearch } from '../../hooks/usePatientSearch';
import type { PatientSummary } from '../../types/walkIn';
import styles from './PatientSearch.module.css';

interface PatientSearchProps {
  onSelect: (patient: PatientSummary) => void;
  onCreateNew: () => void;
}

export function PatientSearch({ onSelect, onCreateNew }: PatientSearchProps) {
  const { term, setTerm, results, isSearching, error, reset } = usePatientSearch();
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSelect = useCallback(
    (patient: PatientSummary) => {
      reset();
      onSelect(patient);
    },
    [reset, onSelect]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') reset();
  };

  const showResults = !isSearching && term.trim().length >= 2;

  return (
    <section className={styles.container} aria-label="Patient search">
      <h2 className={styles.heading}>Find Patient</h2>
      <p className={styles.hint}>
        Search by name, phone, email, or patient ID
      </p>

      <div className={styles.inputWrapper}>
        <label htmlFor="patient-search" className={styles.srOnly}>
          Search patients
        </label>
        <input
          id="patient-search"
          ref={inputRef}
          type="search"
          className={styles.input}
          value={term}
          onChange={e => setTerm(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type to search…"
          autoComplete="off"
          aria-autocomplete="list"
          aria-controls="search-results"
          aria-busy={isSearching}
        />
        {isSearching && (
          <div className={styles.spinner} aria-hidden="true" />
        )}
      </div>

      {error && (
        <div className={styles.errorMsg} role="alert">
          {error}
          <button
            type="button"
            className={styles.retryBtn}
            onClick={() => setTerm(t => t + ' ')}
          >
            Retry
          </button>
        </div>
      )}

      {showResults && (
        <ul
          id="search-results"
          className={styles.resultList}
          role="listbox"
          aria-label="Patient search results"
        >
          {results.length === 0 ? (
            <li className={styles.noMatch} role="option" aria-selected={false}>
              <span>No patients found for &ldquo;{term}&rdquo;.</span>
              <button
                type="button"
                className={styles.createBtn}
                onClick={onCreateNew}
              >
                + Create New Patient
              </button>
            </li>
          ) : (
            results.map(patient => (
              <li
                key={patient.id}
                className={styles.resultRow}
                role="option"
                aria-selected={false}
                onClick={() => handleSelect(patient)}
                onKeyDown={e => {
                  if (e.key === 'Enter' || e.key === ' ') handleSelect(patient);
                }}
                tabIndex={0}
              >
                <span className={styles.name}>{patient.fullName}</span>
                <span className={styles.meta}>
                  DOB: {patient.dateOfBirth} &bull; {patient.phone}
                  {patient.email && ` · ${patient.email}`}
                </span>
              </li>
            ))
          )}
        </ul>
      )}
    </section>
  );
}
