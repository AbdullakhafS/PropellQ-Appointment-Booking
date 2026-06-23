namespace PropelIQ.Domain.Entities;

/// <summary>
/// Immutable audit entry for every create / update / void action on an IntakeResponse.
/// </summary>
public sealed class IntakeAuditLog
{
    public int Id { get; private set; }
    public int IntakeId { get; private set; }
    public string Action { get; private set; } = string.Empty;   // "create" | "update" | "void"
    public string? ChangedField { get; private set; }
    public string? OldValue { get; private set; }
    public string? NewValue { get; private set; }
    public string? ChangedBy { get; private set; }
    public string? Reason { get; private set; }
    public DateTimeOffset ChangedAt { get; private set; }

    private IntakeAuditLog() { }

    public static IntakeAuditLog Create(
        int intakeId,
        string action,
        string? changedField,
        string? oldValue,
        string? newValue,
        string? changedBy,
        string? reason)
        => new()
        {
            IntakeId = intakeId,
            Action = action,
            ChangedField = changedField,
            OldValue = oldValue,
            NewValue = newValue,
            ChangedBy = changedBy,
            Reason = reason,
            ChangedAt = DateTimeOffset.UtcNow
        };
}
