namespace PropelIQ.Api.DTOs.Queue;

public sealed record QueueStatsDto(
    int ActivePatientCount,
    int WalkInCount,
    int ArrivedCount,
    double AverageWaitMinutes,
    double MaxWaitMinutes,
    string WaitHealth,          // "Normal" | "Warning" | "Critical"
    int WaitWarningThreshold,   // minutes
    int WaitCriticalThreshold,  // minutes
    DateTimeOffset ComputedAt
);
