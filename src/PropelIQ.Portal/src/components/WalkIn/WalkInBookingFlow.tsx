import React, { useState, useCallback } from 'react';
import { PatientSearch } from './PatientSearch';
import { NewPatientModal } from './NewPatientModal';
import { SlotPicker } from './SlotPicker';
import { walkInApi } from '../../api/walkInApi';
import type { PatientSummary, WalkInAppointment, WalkInStep } from '../../types/walkIn';
import type { SelectedSlot } from '../../types/slot';
import styles from './WalkInBookingFlow.module.css';

interface BookingFormState {
  providerName: string;
  appointmentDate: string;
  appointmentTime: string;
  durationMinutes: number;
  notes: string;
}

const EMPTY_FORM: BookingFormState = {
  providerName: '',
  appointmentDate: '',
  appointmentTime: '',
  durationMinutes: 30,
  notes: '',
};

interface WalkInBookingFlowProps {
  onComplete?: (appointment: WalkInAppointment) => void;
}

export function WalkInBookingFlow({ onComplete }: WalkInBookingFlowProps) {
  const [step, setStep] = useState<WalkInStep>('search');
  const [selectedPatient, setSelectedPatient] = useState<PatientSummary | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<SelectedSlot | null>(null);
  const [slotConflictError, setSlotConflictError] = useState<string | null>(null);
  const [bookingForm, setBookingForm] = useState<BookingFormState>(EMPTY_FORM);
  const [bookingErrors, setBookingErrors] = useState<Partial<Record<keyof BookingFormState, string>>>({});
  const [submitting, setSubmitting] = useState(false);
  const [bookingError, setBookingError] = useState<string | null>(null);
  const [confirmedAppointment, setConfirmedAppointment] = useState<WalkInAppointment | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const handlePatientSelected = useCallback((patient: PatientSummary) => {
    setSelectedPatient(patient);
    setStep('book');
  }, []);

  const handlePatientCreated = useCallback((patient: PatientSummary) => {
    setSelectedPatient(patient);
    setStep('book');
  }, []);

  const setField = (key: keyof BookingFormState, value: string | number) =>
    setBookingForm(prev => ({ ...prev, [key]: value }));

  const validateBooking = (): boolean => {
    // When a slot is selected, the slot provides provider/time — no manual fields needed.
    if (selectedSlot) return true;

    const errs: Partial<Record<keyof BookingFormState, string>> = {};
    if (!bookingForm.providerName.trim()) errs.providerName = 'Provider name is required.';
    if (!bookingForm.appointmentDate) errs.appointmentDate = 'Appointment date is required.';
    if (!bookingForm.appointmentTime) errs.appointmentTime = 'Appointment time is required.';
    setBookingErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleBookingSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitted || !selectedPatient) return;
    if (!validateBooking()) return;

    setBookingError(null);
    setSlotConflictError(null);
    setSubmitting(true);

    try {
      const appointmentTime = selectedSlot
        ? selectedSlot.startTime
        : new Date(`${bookingForm.appointmentDate}T${bookingForm.appointmentTime}`).toISOString();

      const durationMinutes = selectedSlot
        ? selectedSlot.durationMinutes
        : bookingForm.durationMinutes;

      const providerName = selectedSlot
        ? selectedSlot.providerName
        : bookingForm.providerName.trim();

      const result = await walkInApi.bookWalkIn({
        patientId: selectedPatient.id,
        providerName,
        appointmentTime,
        durationMinutes,
        notes: bookingForm.notes.trim() || undefined,
        slotId: selectedSlot?.slotId,
        slotVersion: selectedSlot?.version,
      });

      setConfirmedAppointment(result);
      setSubmitted(true);
      setStep('confirm');
      onComplete?.(result);
    } catch (err: unknown) {
      // 409 = slot conflict — preserve data and surface reselection guidance
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        setSlotConflictError('The selected slot was just taken. Please choose another.');
        setSelectedSlot(null);
      } else {
        setBookingError('Booking failed. Your selections are preserved — please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleStartOver = () => {
    setStep('search');
    setSelectedPatient(null);
    setSelectedSlot(null);
    setSlotConflictError(null);
    setBookingForm(EMPTY_FORM);
    setBookingErrors({});
    setBookingError(null);
    setConfirmedAppointment(null);
    setSubmitted(false);
  };

  return (
    <div className={styles.flow}>
      {/* Breadcrumb */}
      <nav className={styles.breadcrumb} aria-label="Walk-in booking steps">
        <StepIndicator label="Search Patient" active={step === 'search'} done={['book', 'confirm'].includes(step)} />
        <span className={styles.sep} aria-hidden="true">›</span>
        <StepIndicator label="Book Appointment" active={step === 'book'} done={step === 'confirm'} />
        <span className={styles.sep} aria-hidden="true">›</span>
        <StepIndicator label="Confirmation" active={step === 'confirm'} done={false} />
      </nav>

      <div className={styles.content}>
        {/* STEP: Search */}
        {step === 'search' && (
          <PatientSearch
            onSelect={handlePatientSelected}
            onCreateNew={() => setStep('create')}
          />
        )}

        {/* STEP: Create new patient */}
        {step === 'create' && (
          <NewPatientModal
            onCreated={handlePatientCreated}
            onCancel={() => setStep('search')}
          />
        )}

        {/* STEP: Book */}
        {step === 'book' && selectedPatient && (
          <section aria-labelledby="booking-heading" className={styles.bookingSection}>
            <h2 id="booking-heading" className={styles.sectionHeading}>Book Walk-In Appointment</h2>

            <div className={styles.patientBadge}>
              <span className={styles.walkInTag} aria-label="Walk-in indicator">Walk-In</span>
              <strong>{selectedPatient.fullName}</strong>
              <span className={styles.patientMeta}>
                DOB: {selectedPatient.dateOfBirth} · {selectedPatient.phone}
              </span>
              <button
                type="button"
                className={styles.changePatientBtn}
                onClick={() => { setSelectedPatient(null); setStep('search'); }}
              >
                Change
              </button>
            </div>

            {bookingError && (
              <div className={styles.bookingError} role="alert">{bookingError}</div>
            )}

            {/* Slot picker (task_032_001 / task_032_002 / task_032_004) */}
            <SlotPicker
              query={{ windowHours: 8 }}
              selectedSlot={selectedSlot}
              onSelect={setSelectedSlot}
              onClearSelection={() => setSelectedSlot(null)}
              conflictError={slotConflictError}
            />

            <form onSubmit={handleBookingSubmit} noValidate className={styles.bookingForm}>
              <div className={styles.formField}>
                <label htmlFor="providerName" className={styles.formLabel}>Provider Name *</label>
                <input
                  id="providerName"
                  type="text"
                  className={`${styles.formInput} ${bookingErrors.providerName ? styles.inputError : ''}`}
                  value={bookingForm.providerName}
                  onChange={e => setField('providerName', e.target.value)}
                  placeholder="Dr. Smith"
                />
                {bookingErrors.providerName && <span className={styles.errorText} role="alert">{bookingErrors.providerName}</span>}
              </div>

              <div className={styles.formRow}>
                <div className={styles.formField}>
                  <label htmlFor="apptDate" className={styles.formLabel}>Date *</label>
                  <input
                    id="apptDate"
                    type="date"
                    className={`${styles.formInput} ${bookingErrors.appointmentDate ? styles.inputError : ''}`}
                    value={bookingForm.appointmentDate}
                    onChange={e => setField('appointmentDate', e.target.value)}
                  />
                  {bookingErrors.appointmentDate && <span className={styles.errorText} role="alert">{bookingErrors.appointmentDate}</span>}
                </div>

                <div className={styles.formField}>
                  <label htmlFor="apptTime" className={styles.formLabel}>Time *</label>
                  <input
                    id="apptTime"
                    type="time"
                    className={`${styles.formInput} ${bookingErrors.appointmentTime ? styles.inputError : ''}`}
                    value={bookingForm.appointmentTime}
                    onChange={e => setField('appointmentTime', e.target.value)}
                  />
                  {bookingErrors.appointmentTime && <span className={styles.errorText} role="alert">{bookingErrors.appointmentTime}</span>}
                </div>
              </div>

              <div className={styles.formField}>
                <label htmlFor="duration" className={styles.formLabel}>Duration (minutes)</label>
                <select
                  id="duration"
                  className={styles.formInput}
                  value={bookingForm.durationMinutes}
                  onChange={e => setField('durationMinutes', Number(e.target.value))}
                >
                  {[15, 30, 45, 60, 90].map(d => (
                    <option key={d} value={d}>{d} min</option>
                  ))}
                </select>
              </div>

              <div className={styles.formField}>
                <label htmlFor="notes" className={styles.formLabel}>Notes</label>
                <textarea
                  id="notes"
                  className={styles.formInput}
                  value={bookingForm.notes}
                  onChange={e => setField('notes', e.target.value)}
                  rows={2}
                  placeholder="Optional visit notes…"
                />
              </div>

              <div className={styles.formActions}>
                <button
                  type="button"
                  className={styles.backBtn}
                  onClick={() => setStep('search')}
                  disabled={submitting}
                >
                  ← Back
                </button>
                <button
                  type="submit"
                  className={styles.submitBtn}
                  disabled={submitting || submitted}
                  aria-disabled={submitting || submitted}
                >
                  {submitting ? 'Booking…' : 'Confirm Walk-In Booking'}
                </button>
              </div>
            </form>
          </section>
        )}

        {/* STEP: Confirmation */}
        {step === 'confirm' && confirmedAppointment && (
          <BookingConfirmation
            appointment={confirmedAppointment}
            onNewBooking={handleStartOver}
          />
        )}
      </div>
    </div>
  );
}

// --- Step indicator sub-component ---

function StepIndicator({ label, active, done }: { label: string; active: boolean; done: boolean }) {
  return (
    <span
      className={`${styles.step} ${active ? styles.stepActive : ''} ${done ? styles.stepDone : ''}`}
      aria-current={active ? 'step' : undefined}
    >
      {label}
    </span>
  );
}

// --- Confirmation sub-component (task_031_004) ---

interface BookingConfirmationProps {
  appointment: WalkInAppointment;
  onNewBooking: () => void;
}

function BookingConfirmation({ appointment, onNewBooking }: BookingConfirmationProps) {
  const apptDate = new Date(appointment.appointmentTime);

  return (
    <section
      className={styles.confirmation}
      aria-labelledby="confirm-heading"
      tabIndex={-1}
    >
      <div className={styles.confirmIcon} aria-hidden="true">✓</div>
      <h2 id="confirm-heading" className={styles.confirmHeading}>
        Walk-In Booking Confirmed
      </h2>

      <dl className={styles.confirmDetails}>
        <dt>Patient</dt>
        <dd>{appointment.patientFullName}</dd>

        <dt>Provider</dt>
        <dd>{appointment.providerName}</dd>

        <dt>Date &amp; Time</dt>
        <dd>
          {apptDate.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}{' '}
          at {apptDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </dd>

        <dt>Duration</dt>
        <dd>{appointment.durationMinutes} minutes</dd>

        <dt>Status</dt>
        <dd>
          <span className={styles.walkInTag} aria-label="Walk-in appointment">Walk-In</span>
          {' '}{appointment.status}
        </dd>

        <dt>Reference</dt>
        <dd className={styles.refId}>{appointment.appointmentId}</dd>
      </dl>

      <div className={styles.confirmActions}>
        <button
          type="button"
          className={styles.submitBtn}
          onClick={onNewBooking}
          autoFocus
        >
          + New Walk-In Booking
        </button>
      </div>
    </section>
  );
}
