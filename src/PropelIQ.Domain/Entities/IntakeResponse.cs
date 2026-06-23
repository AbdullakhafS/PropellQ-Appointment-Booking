namespace PropelIQ.Domain.Entities;

/// <summary>
/// Master record representing one completed intake per appointment.
/// Never hard-deleted; set Status = "voided" to invalidate.
/// </summary>
public sealed class IntakeResponse
{
    public int Id { get; private set; }
    public int AppointmentId { get; private set; }
    public int PatientId { get; private set; }
    public string Mode { get; private set; } = string.Empty;       // "ai" | "manual"
    public string Status { get; private set; } = "completed";      // "completed" | "voided"
    public DateTimeOffset CompletedAt { get; private set; }
    public DateTimeOffset CreatedAt { get; private set; }
    public DateTimeOffset UpdatedAt { get; private set; }
    public int? CreatedByStaffId { get; private set; }
    public string? Notes { get; private set; }
    public string? ChiefComplaint { get; private set; }

    public IList<IntakeMedicalHistory> MedicalHistory { get; private set; } = [];
    public IList<IntakeMedication> Medications { get; private set; } = [];
    public IList<IntakeAllergy> Allergies { get; private set; } = [];
    public IntakeInsurance? InsuranceInfo { get; private set; }

    private IntakeResponse() { }

    public static IntakeResponse Create(
        int appointmentId,
        int patientId,
        string mode,
        string? chiefComplaint,
        string? notes,
        int? createdByStaffId)
        => new()
        {
            AppointmentId = appointmentId,
            PatientId = patientId,
            Mode = mode,
            Status = "completed",
            ChiefComplaint = chiefComplaint,
            Notes = notes,
            CreatedByStaffId = createdByStaffId,
            CompletedAt = DateTimeOffset.UtcNow,
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow
        };

    public void Void(string? reason)
    {
        Status = "voided";
        Notes = string.IsNullOrWhiteSpace(reason) ? Notes : reason;
        UpdatedAt = DateTimeOffset.UtcNow;
    }

    public void UpdateChiefComplaintAndTimestamp(string? newChiefComplaint)
    {
        ChiefComplaint = newChiefComplaint;
        UpdatedAt = DateTimeOffset.UtcNow;
    }

    public void AddMedicalHistory(IntakeMedicalHistory entry) => MedicalHistory.Add(entry);
    public void AddMedication(IntakeMedication entry) => Medications.Add(entry);
    public void AddAllergy(IntakeAllergy entry) => Allergies.Add(entry);
    public void SetInsurance(IntakeInsurance info) => InsuranceInfo = info;
}
