import type { InsurancePreCheckResult } from './insurance';

export interface MedicationRow {
  name: string;
  dosage: string;
  frequency: string;
}

export interface AllergyRow {
  allergen: string;
  reaction: string;
  type: 'DrugAllergy' | 'SideEffect' | 'Unknown';
}

export interface InsuranceFormData {
  provider: string;
  memberId: string;
  groupNumber: string;
  planName: string;
}

export interface ManualIntakeFormData {
  chiefComplaint: string;
  medicalHistory: string[];
  otherConditions: string;
  medications: MedicationRow[];
  allergies: AllergyRow[];
  insuranceInfo: InsuranceFormData;
}

export interface LastIntakeResponse {
  chiefComplaint: string | null;
  medicalHistory: string[];
  otherConditions: string | null;
  medications: MedicationRow[];
  allergies: AllergyRow[];
  insuranceInfo: InsuranceFormData | null;
  lastUpdatedAt: string;
}

export interface SubmitManualIntakeRequest {
  appointmentId: number;
  patientId: number;
  chiefComplaint: string;
  medicalHistory: string[];
  otherConditions?: string;
  medications: MedicationRow[];
  allergies: AllergyRow[];
  insuranceInfo?: InsuranceFormData;
}

export interface SubmitManualIntakeResponse {
  conversationId: number;
  insuranceCheck?: InsurancePreCheckResult;
}
