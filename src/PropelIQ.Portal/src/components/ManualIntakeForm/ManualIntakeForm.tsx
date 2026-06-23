import React, { useState, useEffect, useCallback } from 'react';
import { manualIntakeApi } from '../../api/manualIntakeApi';
import type {
  ManualIntakeFormData,
  MedicationRow,
  AllergyRow,
  LastIntakeResponse,
} from '../../types/intake';
import styles from './ManualIntakeForm.module.css';

const COMMON_CONDITIONS = [
  'Diabetes',
  'Asthma',
  'Hypertension',
  'Heart Disease',
  'COPD',
  'Arthritis',
  'Depression / Anxiety',
  'Thyroid Disorder',
];

const EMPTY_FORM: ManualIntakeFormData = {
  chiefComplaint: '',
  medicalHistory: [],
  otherConditions: '',
  medications: [],
  allergies: [],
  insuranceInfo: { provider: '', memberId: '', groupNumber: '', planName: '' },
};

function emptyMedRow(): MedicationRow {
  return { name: '', dosage: '', frequency: '' };
}

function emptyAllergyRow(): AllergyRow {
  return { allergen: '', reaction: '', type: 'Unknown' };
}

function hydrateFromPrevious(prev: LastIntakeResponse): ManualIntakeFormData {
  return {
    chiefComplaint: prev.chiefComplaint ?? '',
    medicalHistory: prev.medicalHistory ?? [],
    otherConditions: prev.otherConditions ?? '',
    medications: prev.medications.length > 0 ? prev.medications : [],
    allergies: prev.allergies.length > 0 ? prev.allergies : [],
    insuranceInfo: prev.insuranceInfo
      ? {
          provider: prev.insuranceInfo.provider ?? '',
          memberId: prev.insuranceInfo.memberId ?? '',
          groupNumber: prev.insuranceInfo.groupNumber ?? '',
          planName: prev.insuranceInfo.planName ?? '',
        }
      : EMPTY_FORM.insuranceInfo,
  };
}

type LoadState = 'loading' | 'consent' | 'ready' | 'error';

interface ManualIntakeFormProps {
  appointmentId: number;
  patientId: number;
  /** Pre-populated values injected when switching from another mode. */
  seed?: Partial<ManualIntakeFormData>;
  /** Called whenever the form data changes (used by the mode shell to capture data before a switch). */
  onFormChange?: (data: ManualIntakeFormData) => void;
  onSubmitSuccess: (conversationId: number) => void;
}

export function ManualIntakeForm({ appointmentId, patientId, seed, onFormChange, onSubmitSuccess }: ManualIntakeFormProps) {
  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [previousData, setPreviousData] = useState<LastIntakeResponse | null>(null);
  const [formData, setFormData] = useState<ManualIntakeFormData>(EMPTY_FORM);
  const [activeSection, setActiveSection] = useState<number>(0);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (seed && Object.keys(seed).length > 0) {
      setFormData(prev => ({ ...prev, ...seed }));
      setLoadState('ready');
    } else {
      manualIntakeApi.getLastIntake(patientId)
        .then(prev => {
          if (prev) {
            setPreviousData(prev);
            setLoadState('consent');
          } else {
            setLoadState('ready');
          }
        })
        .catch(() => setLoadState('error'));
    }
  }, [patientId, seed]);

  // Notify parent of form changes for cross-mode data capture
  useEffect(() => {
    onFormChange?.(formData);
  }, [formData, onFormChange]);

  const handleUsePrevious = useCallback(() => {
    if (previousData) {
      setFormData(hydrateFromPrevious(previousData));
    }
    setLoadState('ready');
  }, [previousData]);

  const handleStartFresh = useCallback(() => {
    setFormData(EMPTY_FORM);
    setLoadState('ready');
  }, []);

  // --- field helpers ---
  const setField = <K extends keyof ManualIntakeFormData>(key: K, value: ManualIntakeFormData[K]) =>
    setFormData(prev => ({ ...prev, [key]: value }));

  const toggleCondition = (condition: string) => {
    setFormData(prev => {
      const has = prev.medicalHistory.includes(condition);
      return {
        ...prev,
        medicalHistory: has
          ? prev.medicalHistory.filter(c => c !== condition)
          : [...prev.medicalHistory, condition],
      };
    });
  };

  const updateMed = (index: number, key: keyof MedicationRow, value: string) =>
    setFormData(prev => {
      const meds = [...prev.medications];
      meds[index] = { ...meds[index], [key]: value };
      return { ...prev, medications: meds };
    });

  const removeMed = (index: number) =>
    setFormData(prev => ({ ...prev, medications: prev.medications.filter((_, i) => i !== index) }));

  const updateAllergy = (index: number, key: keyof AllergyRow, value: string) =>
    setFormData(prev => {
      const rows = [...prev.allergies];
      rows[index] = { ...rows[index], [key]: value } as AllergyRow;
      return { ...prev, allergies: rows };
    });

  const removeAllergy = (index: number) =>
    setFormData(prev => ({ ...prev, allergies: prev.allergies.filter((_, i) => i !== index) }));

  const setInsurance = (key: keyof ManualIntakeFormData['insuranceInfo'], value: string) =>
    setFormData(prev => ({ ...prev, insuranceInfo: { ...prev.insuranceInfo, [key]: value } }));

  // --- validation ---
  const validate = (): Record<string, string> => {
    const errs: Record<string, string> = {};

    if (!formData.chiefComplaint.trim())
      errs.chiefComplaint = 'Chief complaint is required.';

    const ins = formData.insuranceInfo;
    const hasAnyInsurance =
      ins.provider.trim() || ins.memberId.trim() || ins.groupNumber.trim() || ins.planName.trim();
    if (hasAnyInsurance) {
      if (!ins.provider.trim()) errs.insuranceProvider = 'Insurance name is required when entering insurance details.';
      if (!ins.memberId.trim()) errs.insuranceMemberId = 'Member ID is required when entering insurance details.';
    }

    return errs;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    const errs = validate();
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      // Jump to first section with an error
      if (errs.chiefComplaint) setActiveSection(0);
      else if (errs.insuranceProvider || errs.insuranceMemberId) setActiveSection(4);
      return;
    }

    setErrors({});
    setIsSubmitting(true);

    const ins = formData.insuranceInfo;
    const hasInsurance = !!(ins.provider.trim() || ins.memberId.trim());

    try {
      const result = await manualIntakeApi.submit({
        appointmentId,
        patientId,
        chiefComplaint: formData.chiefComplaint.trim(),
        medicalHistory: formData.medicalHistory,
        otherConditions: formData.otherConditions.trim() || undefined,
        medications: formData.medications.filter(m => m.name.trim()),
        allergies: formData.allergies.filter(a => a.allergen.trim()),
        insuranceInfo: hasInsurance ? ins : undefined,
      });
      onSubmitSuccess(result.conversationId);
    } catch {
      setSubmitError('Submission failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loadState === 'loading') {
    return (
      <div className={styles.centred} role="status" aria-live="polite">
        <div className={styles.spinner} aria-hidden="true" />
        <p>Loading your information…</p>
      </div>
    );
  }

  if (loadState === 'error') {
    return (
      <div className={styles.centred} role="alert">
        <p className={styles.errorText}>Unable to load your previous data. Please refresh and try again.</p>
      </div>
    );
  }

  if (loadState === 'consent' && previousData) {
    return (
      <div className={styles.consent} role="dialog" aria-labelledby="consent-heading">
        <h2 id="consent-heading" className={styles.consentHeading}>Use Your Previous Information?</h2>
        <p className={styles.consentBody}>
          We have your information from a previous visit
          {' '}(<time dateTime={previousData.lastUpdatedAt}>
            last updated {new Date(previousData.lastUpdatedAt).toLocaleDateString()}
          </time>).
          Would you like to use it to save time?
        </p>
        <div className={styles.consentActions}>
          <button
            type="button"
            className={styles.primaryBtn}
            onClick={handleUsePrevious}
            autoFocus
          >
            Use Previous
          </button>
          <button
            type="button"
            className={styles.secondaryBtn}
            onClick={handleStartFresh}
          >
            Start Fresh
          </button>
        </div>
      </div>
    );
  }

  const sections = ['Chief Complaint', 'Medical History', 'Current Medications', 'Allergies', 'Insurance'];

  return (
    <form
      className={styles.form}
      onSubmit={handleSubmit}
      noValidate
      aria-label="Manual intake form"
    >
      <h1 className={styles.formTitle}>Patient Intake Form</h1>

      {Object.keys(errors).length > 0 && (
        <div className={styles.errorSummary} role="alert" aria-live="assertive">
          <strong>Please fix the following before submitting:</strong>
          <ul>
            {Object.values(errors).map((msg, i) => <li key={i}>{msg}</li>)}
          </ul>
        </div>
      )}

      {submitError && (
        <div className={styles.errorSummary} role="alert">{submitError}</div>
      )}

      {/* Section tabs */}
      <nav className={styles.tabs} aria-label="Form sections">
        {sections.map((label, i) => (
          <button
            key={i}
            type="button"
            className={`${styles.tab} ${activeSection === i ? styles.tabActive : ''}`}
            onClick={() => setActiveSection(i)}
            aria-selected={activeSection === i}
            aria-controls={`section-${i}`}
          >
            {label}
          </button>
        ))}
      </nav>

      {/* Section 0: Chief Complaint */}
      <section id="section-0" className={styles.section} hidden={activeSection !== 0} aria-labelledby="s0-heading">
        <h2 id="s0-heading" className={styles.sectionHeading}>Chief Complaint</h2>
        <div className={styles.field}>
          <label htmlFor="chiefComplaint" className={styles.label}>
            What brings you in today? <span aria-hidden="true" className={styles.required}>*</span>
          </label>
          <textarea
            id="chiefComplaint"
            className={`${styles.textarea} ${errors.chiefComplaint ? styles.fieldError : ''}`}
            value={formData.chiefComplaint}
            onChange={e => setField('chiefComplaint', e.target.value)}
            rows={4}
            aria-required="true"
            aria-describedby={errors.chiefComplaint ? 'cc-error' : undefined}
          />
          {errors.chiefComplaint && (
            <span id="cc-error" className={styles.errorMsg} role="alert">{errors.chiefComplaint}</span>
          )}
        </div>
      </section>

      {/* Section 1: Medical History */}
      <section id="section-1" className={styles.section} hidden={activeSection !== 1} aria-labelledby="s1-heading">
        <h2 id="s1-heading" className={styles.sectionHeading}>Medical History</h2>
        <fieldset className={styles.checkboxGroup}>
          <legend className={styles.label}>Do you have any of the following conditions?</legend>
          {COMMON_CONDITIONS.map(c => (
            <label key={c} className={styles.checkboxLabel}>
              <input
                type="checkbox"
                className={styles.checkbox}
                checked={formData.medicalHistory.includes(c)}
                onChange={() => toggleCondition(c)}
              />
              {c}
            </label>
          ))}
        </fieldset>
        <div className={styles.field}>
          <label htmlFor="otherConditions" className={styles.label}>Other conditions</label>
          <textarea
            id="otherConditions"
            className={styles.textarea}
            value={formData.otherConditions}
            onChange={e => setField('otherConditions', e.target.value)}
            rows={3}
            placeholder="Describe any other conditions not listed above…"
          />
        </div>
      </section>

      {/* Section 2: Medications */}
      <section id="section-2" className={styles.section} hidden={activeSection !== 2} aria-labelledby="s2-heading">
        <h2 id="s2-heading" className={styles.sectionHeading}>Current Medications</h2>
        {formData.medications.length === 0 && (
          <p className={styles.emptyHint}>No medications added yet.</p>
        )}
        {formData.medications.map((med, i) => (
          <div key={i} className={styles.repeatRow} role="group" aria-label={`Medication ${i + 1}`}>
            <div className={styles.repeatFields}>
              <div className={styles.field}>
                <label htmlFor={`med-name-${i}`} className={styles.label}>Medication name</label>
                <input
                  id={`med-name-${i}`}
                  type="text"
                  className={styles.input}
                  value={med.name}
                  onChange={e => updateMed(i, 'name', e.target.value)}
                  placeholder="e.g. Metformin"
                />
              </div>
              <div className={styles.field}>
                <label htmlFor={`med-dosage-${i}`} className={styles.label}>Dosage</label>
                <input
                  id={`med-dosage-${i}`}
                  type="text"
                  className={styles.input}
                  value={med.dosage}
                  onChange={e => updateMed(i, 'dosage', e.target.value)}
                  placeholder="e.g. 500mg"
                />
              </div>
              <div className={styles.field}>
                <label htmlFor={`med-freq-${i}`} className={styles.label}>Frequency</label>
                <input
                  id={`med-freq-${i}`}
                  type="text"
                  className={styles.input}
                  value={med.frequency}
                  onChange={e => updateMed(i, 'frequency', e.target.value)}
                  placeholder="e.g. Twice daily"
                />
              </div>
            </div>
            <button
              type="button"
              className={styles.deleteBtn}
              onClick={() => removeMed(i)}
              aria-label={`Remove medication ${i + 1}`}
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          className={styles.addBtn}
          onClick={() => setField('medications', [...formData.medications, emptyMedRow()])}
        >
          + Add Medication
        </button>
      </section>

      {/* Section 3: Allergies */}
      <section id="section-3" className={styles.section} hidden={activeSection !== 3} aria-labelledby="s3-heading">
        <h2 id="s3-heading" className={styles.sectionHeading}>Allergies</h2>
        {formData.allergies.length === 0 && (
          <p className={styles.emptyHint}>No allergies added yet.</p>
        )}
        {formData.allergies.map((allergy, i) => (
          <div key={i} className={styles.repeatRow} role="group" aria-label={`Allergy ${i + 1}`}>
            <div className={styles.repeatFields}>
              <div className={styles.field}>
                <label htmlFor={`al-name-${i}`} className={styles.label}>Drug / allergen</label>
                <input
                  id={`al-name-${i}`}
                  type="text"
                  className={styles.input}
                  value={allergy.allergen}
                  onChange={e => updateAllergy(i, 'allergen', e.target.value)}
                  placeholder="e.g. Penicillin"
                />
              </div>
              <div className={styles.field}>
                <label htmlFor={`al-type-${i}`} className={styles.label}>Type</label>
                <select
                  id={`al-type-${i}`}
                  className={styles.input}
                  value={allergy.type}
                  onChange={e => updateAllergy(i, 'type', e.target.value)}
                >
                  <option value="DrugAllergy">Drug Allergy (immune reaction)</option>
                  <option value="SideEffect">Side Effect (e.g. GI upset)</option>
                  <option value="Unknown">Unknown</option>
                </select>
              </div>
              <div className={styles.field}>
                <label htmlFor={`al-reaction-${i}`} className={styles.label}>Reaction details</label>
                <input
                  id={`al-reaction-${i}`}
                  type="text"
                  className={styles.input}
                  value={allergy.reaction}
                  onChange={e => updateAllergy(i, 'reaction', e.target.value)}
                  placeholder="e.g. Rash, difficulty breathing"
                />
              </div>
            </div>
            <button
              type="button"
              className={styles.deleteBtn}
              onClick={() => removeAllergy(i)}
              aria-label={`Remove allergy ${i + 1}`}
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          className={styles.addBtn}
          onClick={() => setField('allergies', [...formData.allergies, emptyAllergyRow()])}
        >
          + Add Allergy
        </button>
      </section>

      {/* Section 4: Insurance */}
      <section id="section-4" className={styles.section} hidden={activeSection !== 4} aria-labelledby="s4-heading">
        <h2 id="s4-heading" className={styles.sectionHeading}>Insurance</h2>
        <div className={styles.twoCol}>
          <div className={styles.field}>
            <label htmlFor="ins-provider" className={styles.label}>Insurance name</label>
            <input
              id="ins-provider"
              type="text"
              className={`${styles.input} ${errors.insuranceProvider ? styles.fieldError : ''}`}
              value={formData.insuranceInfo.provider}
              onChange={e => setInsurance('provider', e.target.value)}
              placeholder="e.g. Aetna"
              aria-describedby={errors.insuranceProvider ? 'ins-provider-error' : undefined}
            />
            {errors.insuranceProvider && (
              <span id="ins-provider-error" className={styles.errorMsg} role="alert">{errors.insuranceProvider}</span>
            )}
          </div>
          <div className={styles.field}>
            <label htmlFor="ins-member" className={styles.label}>Member ID</label>
            <input
              id="ins-member"
              type="text"
              className={`${styles.input} ${errors.insuranceMemberId ? styles.fieldError : ''}`}
              value={formData.insuranceInfo.memberId}
              onChange={e => setInsurance('memberId', e.target.value)}
              placeholder="e.g. 123456789"
              aria-describedby={errors.insuranceMemberId ? 'ins-member-error' : undefined}
            />
            {errors.insuranceMemberId && (
              <span id="ins-member-error" className={styles.errorMsg} role="alert">{errors.insuranceMemberId}</span>
            )}
          </div>
          <div className={styles.field}>
            <label htmlFor="ins-group" className={styles.label}>Group number <span className={styles.optional}>(optional)</span></label>
            <input
              id="ins-group"
              type="text"
              className={styles.input}
              value={formData.insuranceInfo.groupNumber}
              onChange={e => setInsurance('groupNumber', e.target.value)}
              placeholder="e.g. GRP-001"
            />
          </div>
          <div className={styles.field}>
            <label htmlFor="ins-plan" className={styles.label}>Plan name <span className={styles.optional}>(optional)</span></label>
            <input
              id="ins-plan"
              type="text"
              className={styles.input}
              value={formData.insuranceInfo.planName}
              onChange={e => setInsurance('planName', e.target.value)}
              placeholder="e.g. PPO Gold"
            />
          </div>
        </div>
      </section>

      {/* Sticky submit */}
      <div className={styles.submitBar}>
        <button
          type="submit"
          className={styles.submitBtn}
          disabled={isSubmitting}
          aria-disabled={isSubmitting}
        >
          {isSubmitting ? 'Submitting…' : 'Submit Intake'}
        </button>
      </div>
    </form>
  );
}
