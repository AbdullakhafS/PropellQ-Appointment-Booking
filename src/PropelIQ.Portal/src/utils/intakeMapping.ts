import type { ExtractedData, Medication, Allergy } from '../types/chat';
import type { ManualIntakeFormData, MedicationRow, AllergyRow, InsuranceFormData } from '../types/intake';

const COMMON_CONDITIONS = [
  'Diabetes', 'Asthma', 'Hypertension', 'Heart Disease',
  'COPD', 'Arthritis', 'Depression / Anxiety', 'Thyroid Disorder',
];

/**
 * Maps chatbot-extracted data into the manual intake form structure.
 * Preserves all meaningful values; partial / null inputs are handled gracefully.
 */
export function mapExtractedToForm(data: ExtractedData | null | undefined): Partial<ManualIntakeFormData> {
  if (!data) return {};

  // Split medical history: known conditions vs. "Other: ..." entries
  const knownConditions: string[] = [];
  let otherConditions = '';
  for (const entry of data.medicalHistory ?? []) {
    if (entry.startsWith('Other: ')) {
      otherConditions = entry.slice('Other: '.length);
    } else if (COMMON_CONDITIONS.includes(entry)) {
      knownConditions.push(entry);
    } else {
      // Unknown condition string → dump into other
      otherConditions = otherConditions
        ? `${otherConditions}, ${entry}`
        : entry;
    }
  }

  const medications: MedicationRow[] = (data.medications ?? []).map((m: Medication) => ({
    name: m.name ?? '',
    dosage: m.dosage ?? '',
    frequency: m.frequency ?? '',
  }));

  const allergies: AllergyRow[] = (data.allergies ?? []).map((a: Allergy) => ({
    allergen: a.allergen ?? '',
    reaction: a.reaction ?? '',
    type: normaliseAllergyType(a.type),
  }));

  const ins = data.insuranceInfo;
  const insuranceInfo: InsuranceFormData = {
    provider: ins?.provider ?? '',
    memberId: ins?.memberId ?? '',
    groupNumber: ins?.groupNumber ?? '',
    planName: (ins as any)?.planName ?? '',
  };

  return {
    chiefComplaint: data.chiefComplaint ?? '',
    medicalHistory: knownConditions,
    otherConditions,
    medications,
    allergies,
    insuranceInfo,
  };
}

/**
 * Maps manual form data back into the ExtractedData shape used by the chatbot.
 * Used when switching form → chatbot so the chatbot has context on what was entered.
 */
export function mapFormToExtracted(form: ManualIntakeFormData): ExtractedData {
  const history: string[] = [...form.medicalHistory];
  if (form.otherConditions.trim()) {
    history.push(`Other: ${form.otherConditions.trim()}`);
  }

  return {
    chiefComplaint: form.chiefComplaint.trim() || null,
    medicalHistory: history,
    medications: form.medications
      .filter(m => m.name.trim())
      .map(m => ({ name: m.name, dosage: m.dosage || null, frequency: m.frequency || null })),
    allergies: form.allergies
      .filter(a => a.allergen.trim())
      .map(a => ({ allergen: a.allergen, reaction: a.reaction || null, type: a.type })),
    insuranceInfo: hasInsurance(form.insuranceInfo)
      ? {
          provider: form.insuranceInfo.provider || null,
          memberId: form.insuranceInfo.memberId || null,
          groupNumber: form.insuranceInfo.groupNumber || null,
        }
      : null,
  };
}

/**
 * Builds a natural-language summary suitable for injecting into a chatbot conversation
 * when resuming from form data.
 */
export function buildFormSummaryForChatbot(form: ManualIntakeFormData): string {
  const parts: string[] = [];

  if (form.chiefComplaint.trim()) {
    parts.push(`You mentioned you're coming in for: "${form.chiefComplaint.trim()}".`);
  }

  const allHistory = [
    ...form.medicalHistory,
    ...(form.otherConditions.trim() ? [form.otherConditions.trim()] : []),
  ];
  if (allHistory.length > 0) {
    parts.push(`Medical history includes: ${allHistory.join(', ')}.`);
  }

  const meds = form.medications.filter(m => m.name.trim());
  if (meds.length > 0) {
    const medStr = meds.map(m =>
      `${m.name}${m.dosage ? ` ${m.dosage}` : ''}${m.frequency ? ` (${m.frequency})` : ''}`
    ).join(', ');
    parts.push(`You're currently taking: ${medStr}.`);
  }

  const als = form.allergies.filter(a => a.allergen.trim());
  if (als.length > 0) {
    parts.push(`Allergies noted: ${als.map(a => a.allergen).join(', ')}.`);
  }

  if (hasInsurance(form.insuranceInfo)) {
    parts.push(`Insurance: ${form.insuranceInfo.provider || 'provider not specified'}.`);
  }

  return parts.length > 0
    ? `I have some information from your form. ${parts.join(' ')} Is any of this incorrect or would you like to add anything?`
    : 'I can see you started filling out the form. Let\'s continue from where you left off.';
}

function normaliseAllergyType(raw: string | null | undefined): AllergyRow['type'] {
  switch ((raw ?? '').toLowerCase().replace(/[_\s]/g, '')) {
    case 'drugallergy': return 'DrugAllergy';
    case 'sideeffect': return 'SideEffect';
    default: return 'Unknown';
  }
}

function hasInsurance(ins: InsuranceFormData): boolean {
  return !!(ins.provider.trim() || ins.memberId.trim());
}
