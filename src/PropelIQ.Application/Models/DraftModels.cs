namespace PropelIQ.Application.Models;

// --- Draft requests / results ---

public sealed record SaveDraftRequest(
    int AppointmentId,
    int PatientId,
    string Mode,
    string DataJson,
    int SwitchCount
);

public sealed record GetDraftResult(
    string Mode,
    string DataJson,
    int SwitchCount,
    DateTimeOffset LastUpdated,
    DateTimeOffset ExpiresAt
);
