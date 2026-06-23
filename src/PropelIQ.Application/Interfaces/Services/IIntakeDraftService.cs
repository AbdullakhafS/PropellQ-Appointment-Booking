using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

public interface IIntakeDraftService
{
    /// <summary>Returns the active (non-expired) draft for an appointment, or null.</summary>
    Task<GetDraftResult?> GetDraftAsync(int appointmentId, CancellationToken ct = default);

    /// <summary>Creates or updates the draft for an appointment.</summary>
    Task SaveDraftAsync(SaveDraftRequest request, CancellationToken ct = default);

    /// <summary>Deletes the draft after successful submission.</summary>
    Task DeleteDraftAsync(int appointmentId, CancellationToken ct = default);
}
