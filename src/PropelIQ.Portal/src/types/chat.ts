export interface StartChatRequest {
  appointmentId: number;
  patientId: number;
  patientName: string;
}

export interface StartChatResponse {
  conversationId: number;
  welcomeMessage: string;
}

export interface SendMessageRequest {
  conversationId: number;
  appointmentId: number;
  userMessage: string;
}

export interface SendMessageResponse {
  conversationId: number;
  assistantMessage: string;
  extractedData: ExtractedData;
  confidenceScores: ConfidenceScores;
  isComplete: boolean;
  suggestManualFallback: boolean;
}

export interface ConversationHistoryResponse {
  conversationId: number;
  appointmentId: number;
  mode: 'ai' | 'manual';
  transcript: Message[];
  extractedData: ExtractedData;
  confidenceScores: ConfidenceScores;
  isComplete: boolean;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ExtractedData {
  chiefComplaint: string | null;
  medicalHistory: string[];
  medications: Medication[];
  allergies: Allergy[];
  insuranceInfo: InsuranceInfo | null;
}

export interface Medication {
  name: string;
  dosage: string | null;
  frequency: string | null;
}

export interface Allergy {
  allergen: string;
  reaction: string | null;
  type: string;
}

export interface InsuranceInfo {
  provider: string | null;
  memberId: string | null;
  groupNumber: string | null;
}

export interface ConfidenceScores {
  chiefComplaint: number;
  medicalHistory: number;
  medications: number;
  allergies: number;
  insuranceInfo: number;
}
