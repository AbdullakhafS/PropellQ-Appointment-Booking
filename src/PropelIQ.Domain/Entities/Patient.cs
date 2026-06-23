namespace PropelIQ.Domain.Entities;

/// <summary>
/// Core patient demographic record used for walk-in lookup and registration.
/// </summary>
public sealed class Patient
{
    public Guid Id { get; private set; }
    public string FirstName { get; private set; } = string.Empty;
    public string LastName { get; private set; } = string.Empty;
    public DateOnly DateOfBirth { get; private set; }
    public string Phone { get; private set; } = string.Empty;
    public string? Email { get; private set; }
    public string Gender { get; private set; } = string.Empty;
    public string? Address { get; private set; }
    public string? Notes { get; private set; }
    public DateTimeOffset CreatedAt { get; private set; }

    private Patient() { }

    public static Patient Create(
        string firstName,
        string lastName,
        DateOnly dateOfBirth,
        string phone,
        string gender,
        string? email,
        string? address,
        string? notes)
        => new()
        {
            Id = Guid.NewGuid(),
            FirstName = firstName.Trim(),
            LastName = lastName.Trim(),
            DateOfBirth = dateOfBirth,
            Phone = phone.Trim(),
            Gender = gender,
            Email = email?.Trim(),
            Address = address?.Trim(),
            Notes = notes?.Trim(),
            CreatedAt = DateTimeOffset.UtcNow
        };

    public string FullName => $"{FirstName} {LastName}";
}
