using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

public interface IManualIntakeService
{
    /// <summary>
    /// Returns the most recent completed intake for a patient, or null if none exists.
    /// </summary>
    Task<LastIntakeResult?> GetLastIntakeAsync(int patientId, CancellationToken ct = default);

    /// <summary>
    /// Persists a manually submitted intake form as a completed manual intake record.
    /// </summary>
    Task<SubmitManualIntakeResult> SubmitAsync(SubmitManualIntakeRequest request, CancellationToken ct = default);
}
