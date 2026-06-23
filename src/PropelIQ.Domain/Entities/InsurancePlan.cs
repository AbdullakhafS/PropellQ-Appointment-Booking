namespace PropelIQ.Domain.Entities;

/// <summary>
/// A predefined insurance plan used for soft pre-check validation.
/// Aliases and regex format patterns are stored as pipe-delimited strings for EF compatibility.
/// </summary>
public sealed class InsurancePlan
{
    public int Id { get; private set; }
    public string Name { get; private set; } = string.Empty;
    /// <summary>Pipe-delimited list of alternative names, e.g. "Aetna Health|Aetna Insurance".</summary>
    public string AliasesRaw { get; private set; } = string.Empty;
    /// <summary>Regex pattern for member ID validation. Null = no format enforced.</summary>
    public string? MemberIdFormat { get; private set; }
    /// <summary>Regex pattern for group number validation. Null = not enforced.</summary>
    public string? GroupNumberFormat { get; private set; }
    public DateTimeOffset CreatedAt { get; private set; }

    private InsurancePlan() { }

    public static InsurancePlan Create(
        string name,
        string[] aliases,
        string? memberIdFormat,
        string? groupNumberFormat)
        => new()
        {
            Name = name,
            AliasesRaw = string.Join("|", aliases),
            MemberIdFormat = memberIdFormat,
            GroupNumberFormat = groupNumberFormat,
            CreatedAt = DateTimeOffset.UtcNow
        };

    public IReadOnlyList<string> Aliases =>
        string.IsNullOrEmpty(AliasesRaw)
            ? []
            : AliasesRaw.Split('|', StringSplitOptions.RemoveEmptyEntries);
}
