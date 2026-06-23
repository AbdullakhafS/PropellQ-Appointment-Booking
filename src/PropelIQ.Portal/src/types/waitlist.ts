export type WaitlistEntryStatus = 'queued' | 'offered' | 'fulfilled' | 'cancelled';
export type WaitlistOfferStatus = 'pending' | 'accepted' | 'declined' | 'expired';

export interface WaitlistEntry {
  waitlistEntryId: string;
  patientId: string;
  patientFullName: string;
  providerName: string;
  status: WaitlistEntryStatus;
  priority: number;
  createdAt: string;
}

export interface WaitlistOffer {
  offerId: string;
  waitlistEntryId: string;
  patientId: string;
  providerName: string;
  slotStartTime: string;
  status: WaitlistOfferStatus;
  expiresAt: string;
  respondedAt: string | null;
  convertedAppointmentId: string | null;
}

export interface JoinWaitlistRequest {
  patientId: string;
  patientFullName: string;
  providerId: string;
  providerName: string;
  clinicId?: string;
  preferredTimeContext?: string;
}

export interface IssueOfferRequest {
  providerId: string;
  providerName: string;
  slotStartTime: string;
  slotId?: string;
}

export interface OfferConversionResult {
  offerId: string;
  offerStatus: WaitlistOfferStatus;
  appointmentId: string | null;
}
