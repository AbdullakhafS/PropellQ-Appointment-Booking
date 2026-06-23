export type VerificationStatus = 'verified' | 'unverified' | 'manual_review';
export type IntakeMode = 'ai' | 'manual';

export interface ProfileMedicalHistoryItem {
  conditionName: string;
  conditionCode: string | null;
  conditionStatus: string;
  confidenceScore: number;
}

export interface ProfileMedication {
  medicationName: string;
  dosage: string | null;
  frequency: string | null;
  route: string | null;
  confidenceScore: number;
}

export interface ProfileAllergy {
  allergenType: string;
  allergenName: string;
  reactionType: string;
  reactionDescription: string | null;
  severity: string | null;
  confidenceScore: number;
}

export interface ProfileInsurance {
  insuranceName: string | null;
  memberId: string | null;
  groupNumber: string | null;
  planName: string | null;
  verificationStatus: VerificationStatus | null;
  confidenceScore: number | null;
}

export interface ProfileIntake {
  intakeId: number;
  appointmentId: number;
  patientId: number;
  mode: IntakeMode;
  status: string;
  chiefComplaint: string | null;
  completedAt: string;
  updatedAt: string;
  medicalHistory: ProfileMedicalHistoryItem[];
  medications: ProfileMedication[];
  allergies: ProfileAllergy[];
  insurance: ProfileInsurance | null;
}

export interface UpdateIntakePayload {
  chiefComplaint?: string;
  medicalHistory?: { conditionName: string; conditionCode?: string; confidenceScore?: number }[];
  medications?: { medicationName: string; dosage?: string; frequency?: string; route?: string; confidenceScore?: number }[];
  allergies?: { allergenType: string; allergenName: string; reactionType: string; reactionDescription?: string; severity?: string; confidenceScore?: number }[];
  insuranceInfo?: { insuranceName?: string; memberId?: string; groupNumber?: string; planName?: string };
}
