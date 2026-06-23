using PropelIQ.Domain.ValueObjects;

namespace PropelIQ.Application.Models;

// --- Requests ---

public sealed record StartChatRequest(int AppointmentId, int PatientId, string PatientName);

public sealed record SendMessageRequest(
    int ConversationId,
    int AppointmentId,
    string UserMessage
);

// --- Results ---

public sealed record StartChatResult(
    int ConversationId,
    string WelcomeMessage
);

public sealed record SendMessageResult(
    int ConversationId,
    string AssistantMessage,
    ExtractedIntakeDataDto ExtractedData,
    ConfidenceScoresDto ConfidenceScores,
    bool IsComplete,
    bool SuggestManualFallback
);

public sealed record ConversationHistoryResult(
    int ConversationId,
    int AppointmentId,
    string Mode,
    IReadOnlyList<MessageDto> Transcript,
    ExtractedIntakeDataDto ExtractedData,
    ConfidenceScoresDto ConfidenceScores,
    bool IsComplete
);

// --- DTOs ---

public sealed record MessageDto(string Role, string Content, DateTimeOffset Timestamp);

public sealed record ExtractedIntakeDataDto(
    string? ChiefComplaint,
    IReadOnlyList<string> MedicalHistory,
    IReadOnlyList<MedicationEntryDto> Medications,
    IReadOnlyList<AllergyEntryDto> Allergies,
    InsuranceInfoDto? InsuranceInfo
);

public sealed record MedicationEntryDto(string Name, string? Dosage, string? Frequency);

public sealed record AllergyEntryDto(string Allergen, string? Reaction, string Type);

public sealed record InsuranceInfoDto(string? Provider, string? MemberId, string? GroupNumber);

public sealed record ConfidenceScoresDto(
    double ChiefComplaint,
    double MedicalHistory,
    double Medications,
    double Allergies,
    double InsuranceInfo
);
