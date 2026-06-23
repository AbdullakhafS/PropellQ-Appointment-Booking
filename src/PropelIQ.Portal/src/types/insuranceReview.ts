export type VerificationStatus = 'verified' | 'unverified' | 'manual_review';
export type VerificationMethod = 'phone' | 'email' | 'portal' | 'system';

export interface PendingInsuranceRow {
  id: number;
  appointmentId: number;
  patientId: number;
  patientName: string | null;
  insuranceName: string | null;
  memberId: string | null;
  matchedPlanId: number | null;
  matchedPlanName: string | null;
  confidenceScore: number;
  verificationStatus: VerificationStatus;
  appointmentDate: string | null;
  lastVerifiedAt: string | null;
  createdAt: string;
}

export interface PendingInsuranceResponse {
  items: PendingInsuranceRow[];
  totalCount: number;
  page: number;
  pageSize: number;
}

export interface VerifyInsuranceRequest {
  staffId: number;
  newStatus: VerificationStatus;
  verificationMethod: VerificationMethod;
  notes?: string;
}

export interface VerifyInsuranceResponse {
  id: number;
  verificationStatus: VerificationStatus;
  verifiedByStaffId: number;
  verifiedAt: string;
}

export interface BatchVerifyRequest {
  ids: number[];
  staffId: number;
  newStatus: VerificationStatus;
  verificationMethod: VerificationMethod;
  notes?: string;
}

export interface BatchVerifyResponse {
  updated: VerifyInsuranceResponse[];
  failedCount: number;
}

export interface AuditEntry {
  id: number;
  previousStatus: VerificationStatus;
  newStatus: VerificationStatus;
  verifiedByStaffId: number;
  verificationMethod: VerificationMethod;
  notes: string | null;
  verifiedAt: string;
}

export interface PendingQuery {
  status?: string;
  insurance?: string;
  dateRangeDays?: number;
  sortBy?: string;
  sortAsc?: boolean;
  page?: number;
  pageSize?: number;
}
