using System.ComponentModel.DataAnnotations;

namespace PropelIQ.Api.DTOs.Intake;

public sealed record StartChatRequestDto(
    [Required] int AppointmentId,
    [Required] int PatientId,
    [Required, MaxLength(200)] string PatientName
);

public sealed record StartChatResponseDto(
    int ConversationId,
    string WelcomeMessage,
    int CurrentStage,
    int TotalStages
);

public sealed record SendMessageRequestDto(
    [Required] int ConversationId,
    [Required] int AppointmentId,
    [Required, MaxLength(2000)] string UserMessage
);

public sealed record SendMessageResponseDto(
    int ConversationId,
    string AssistantMessage,
    ExtractedDataDto ExtractedData,
    ConfidenceScoresResponseDto ConfidenceScores,
    bool IsComplete,
    bool SuggestManualFallback,
    int CurrentStage,
    int TotalStages
);

public sealed record ConversationHistoryResponseDto(
    int ConversationId,
    int AppointmentId,
    string Mode,
    IReadOnlyList<MessageResponseDto> Transcript,
    ExtractedDataDto ExtractedData,
    ConfidenceScoresResponseDto ConfidenceScores,
    bool IsComplete
);

public sealed record MessageResponseDto(string Role, string Content, DateTimeOffset Timestamp);

public sealed record ExtractedDataDto(
    string? ChiefComplaint,
    IReadOnlyList<string> MedicalHistory,
    IReadOnlyList<MedicationDto> Medications,
    IReadOnlyList<AllergyDto> Allergies,
    InsuranceInfoDto? InsuranceInfo
);

public sealed record MedicationDto(string Name, string? Dosage, string? Frequency);

public sealed record AllergyDto(string Allergen, string? Reaction, string Type);

public sealed record InsuranceInfoDto(string? Provider, string? MemberId, string? GroupNumber, string? PlanName = null);

public sealed record ConfidenceScoresResponseDto(
    double ChiefComplaint,
    double MedicalHistory,
    double Medications,
    double Allergies,
    double InsuranceInfo
);
