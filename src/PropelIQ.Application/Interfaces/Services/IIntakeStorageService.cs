using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

public interface IIntakeStorageService
{
    /// <summary>
    /// Persists a complete intake payload (all sections) in a single transaction.
    /// Writes an audit log entry on completion.
    /// </summary>
    Task<StoreIntakeResult> StoreAsync(StoreIntakeRequest request, CancellationToken ct = default);

    /// <summary>
    /// Returns the latest completed intake for an appointment, or null.
    /// </summary>
    Task<GetIntakeResult?> GetByAppointmentAsync(int appointmentId, CancellationToken ct = default);

    /// <summary>
    /// Returns all completed intakes for a patient (ordered newest first).
    /// </summary>
    Task<IReadOnlyList<GetIntakeResult>> GetByPatientAsync(int patientId, CancellationToken ct = default);

    /// <summary>
    /// Returns the single most recent completed intake for a patient, or null.
    /// Used by the patient profile "Intake" tab.
    /// </summary>
    Task<GetIntakeResult?> GetLatestByPatientAsync(int patientId, CancellationToken ct = default);

    /// <summary>
    /// Applies partial updates to an existing intake record (all sections are replaced).
    /// Writes audit log entries for changed fields.
    /// Throws InvalidOperationException if the intake is voided or not found.
    /// </summary>
    Task<GetIntakeResult> UpdateAsync(UpdateIntakeRequest request, CancellationToken ct = default);

    /// <summary>
    /// Voids an intake (soft-delete). Writes an audit log entry.
    /// </summary>
    Task VoidAsync(int intakeId, string reason, string changedBy, CancellationToken ct = default);
}
