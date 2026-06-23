using System.ComponentModel.DataAnnotations;

namespace PropelIQ.Api.DTOs.Intake;

public sealed record SaveDraftRequestDto(
    [Required] int PatientId,
    [Required, MaxLength(20)] string Mode,
    [Required] string DataJson,
    int SwitchCount
);

public sealed record GetDraftResponseDto(
    string Mode,
    string DataJson,
    int SwitchCount,
    DateTimeOffset LastUpdated,
    DateTimeOffset ExpiresAt
);
