export interface InsurancePreCheckRequest {
  appointmentId: number;
  patientId: number;
  insuranceName?: string;
  memberId?: string;
  groupNumber?: string;
}

export interface InsurancePreCheckResult {
  matchedPlanId: number | null;
  matchedPlanName: string | null;
  confidenceScore: number;
  verificationStatus: 'verified' | 'unverified';
  reason: string;
  isVerified: boolean;
}
