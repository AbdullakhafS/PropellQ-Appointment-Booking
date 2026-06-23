using PropelIQ.Domain.Entities;

namespace PropelIQ.Application.Interfaces.Repositories;

public interface IIntakeDraftRepository
{
    Task<IntakeDraft?> GetByAppointmentIdAsync(int appointmentId, CancellationToken ct = default);
    Task SaveAsync(IntakeDraft draft, CancellationToken ct = default);
    Task DeleteByAppointmentIdAsync(int appointmentId, CancellationToken ct = default);
}
