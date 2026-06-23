import React, { useState } from 'react';
import { walkInApi } from '../../api/walkInApi';
import type { PatientSummary, CreatePatientRequest } from '../../types/walkIn';
import styles from './NewPatientModal.module.css';

interface NewPatientModalProps {
  onCreated: (patient: PatientSummary) => void;
  onCancel: () => void;
}

interface FormState {
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  phone: string;
  gender: string;
  email: string;
  address: string;
  notes: string;
}

const EMPTY: FormState = {
  firstName: '',
  lastName: '',
  dateOfBirth: '',
  phone: '',
  gender: '',
  email: '',
  address: '',
  notes: '',
};

type FieldErrors = Partial<Record<keyof FormState, string>>;

function validate(f: FormState): FieldErrors {
  const errs: FieldErrors = {};
  if (!f.firstName.trim()) errs.firstName = 'First name is required.';
  if (!f.lastName.trim()) errs.lastName = 'Last name is required.';
  if (!f.dateOfBirth) errs.dateOfBirth = 'Date of birth is required.';
  if (!f.phone.trim()) errs.phone = 'Phone is required.';
  else if (!/^[\d\s\-+().]{7,20}$/.test(f.phone.trim())) errs.phone = 'Invalid phone format.';
  if (!f.gender) errs.gender = 'Gender is required.';
  if (f.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email.trim()))
    errs.email = 'Invalid email format.';
  return errs;
}

export function NewPatientModal({ onCreated, onCancel }: NewPatientModalProps) {
  const [form, setForm] = useState<FormState>(EMPTY);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const setField = (key: keyof FormState, value: string) =>
    setForm(prev => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);

    const errs = validate(form);
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      return;
    }
    setErrors({});
    setSubmitting(true);

    try {
      const request: CreatePatientRequest = {
        firstName: form.firstName.trim(),
        lastName: form.lastName.trim(),
        dateOfBirth: form.dateOfBirth,
        phone: form.phone.trim(),
        gender: form.gender,
        email: form.email.trim() || undefined,
        address: form.address.trim() || undefined,
        notes: form.notes.trim() || undefined,
      };
      const created = await walkInApi.createPatient(request);
      onCreated(created);
    } catch {
      setApiError('Failed to create patient. Please check the details and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className={styles.overlay}
      role="dialog"
      aria-modal="true"
      aria-labelledby="new-patient-heading"
    >
      <div className={styles.modal}>
        <header className={styles.modalHeader}>
          <h2 id="new-patient-heading" className={styles.modalTitle}>
            New Patient Registration
          </h2>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={onCancel}
            aria-label="Close"
          >
            ✕
          </button>
        </header>

        <form onSubmit={handleSubmit} noValidate className={styles.form}>
          {apiError && (
            <div className={styles.apiError} role="alert">{apiError}</div>
          )}

          <div className={styles.row}>
            <Field
              id="firstName"
              label="First Name *"
              value={form.firstName}
              error={errors.firstName}
              onChange={v => setField('firstName', v)}
            />
            <Field
              id="lastName"
              label="Last Name *"
              value={form.lastName}
              error={errors.lastName}
              onChange={v => setField('lastName', v)}
            />
          </div>

          <div className={styles.row}>
            <Field
              id="dateOfBirth"
              label="Date of Birth *"
              type="date"
              value={form.dateOfBirth}
              error={errors.dateOfBirth}
              onChange={v => setField('dateOfBirth', v)}
            />
            <Field
              id="phone"
              label="Phone *"
              type="tel"
              value={form.phone}
              error={errors.phone}
              onChange={v => setField('phone', v)}
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="gender" className={styles.label}>Gender *</label>
            <select
              id="gender"
              className={`${styles.input} ${errors.gender ? styles.inputError : ''}`}
              value={form.gender}
              onChange={e => setField('gender', e.target.value)}
            >
              <option value="">Select…</option>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
              <option value="Non-binary">Non-binary</option>
              <option value="Prefer not to say">Prefer not to say</option>
            </select>
            {errors.gender && <span className={styles.errorText} role="alert">{errors.gender}</span>}
          </div>

          <Field
            id="email"
            label="Email"
            type="email"
            value={form.email}
            error={errors.email}
            onChange={v => setField('email', v)}
          />
          <Field
            id="address"
            label="Address"
            value={form.address}
            onChange={v => setField('address', v)}
          />
          <Field
            id="notes"
            label="Notes"
            value={form.notes}
            onChange={v => setField('notes', v)}
            textarea
          />

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.cancelBtn}
              onClick={onCancel}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={styles.submitBtn}
              disabled={submitting}
            >
              {submitting ? 'Creating…' : 'Create Patient'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// --- Local sub-component ---

interface FieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  error?: string;
  textarea?: boolean;
}

function Field({ id, label, value, onChange, type = 'text', error, textarea }: FieldProps) {
  const cls = `${styles.input} ${error ? styles.inputError : ''}`;
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>{label}</label>
      {textarea ? (
        <textarea
          id={id}
          className={cls}
          value={value}
          onChange={e => onChange(e.target.value)}
          rows={2}
        />
      ) : (
        <input
          id={id}
          type={type}
          className={cls}
          value={value}
          onChange={e => onChange(e.target.value)}
        />
      )}
      {error && <span className={styles.errorText} role="alert">{error}</span>}
    </div>
  );
}
