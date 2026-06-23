namespace PropelIQ.Application.Models;

// --- Queue statistics ---

/// <summary>Thresholds defining warning and critical wait-time levels (in minutes).</summary>
public static class QueueStatThresholds
{
    public const int WaitWarningMinutes = 20;
    public const int WaitCriticalMinutes = 40;
}

public enum WaitTimeHealth { Normal, Warning, Critical }

public sealed record QueueStats(
    int ActivePatientCount,       // scheduled + arrived (not completed/cancelled)
    int WalkInCount,              // IsWalkIn = true in active set
    int ArrivedCount,             // status = arrived
    double AverageWaitMinutes,    // avg time from AppointmentTime to now for active patients
    double MaxWaitMinutes,        // worst case
    WaitTimeHealth WaitHealth,    // Normal / Warning / Critical based on avg wait
    DateTimeOffset ComputedAt
);
