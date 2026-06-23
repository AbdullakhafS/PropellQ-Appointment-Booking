using PropelIQ.Application.Interfaces.Repositories;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;

namespace PropelIQ.Infrastructure.Draft;

public sealed class IntakeDraftService : IIntakeDraftService
{
    private readonly IIntakeDraftRepository _repo;

    public IntakeDraftService(IIntakeDraftRepository repo) => _repo = repo;

    public async Task<GetDraftResult?> GetDraftAsync(int appointmentId, CancellationToken ct = default)
    {
        var draft = await _repo.GetByAppointmentIdAsync(appointmentId, ct);
        if (draft is null || draft.IsExpired) return null;

        return new GetDraftResult(draft.Mode, draft.DataJson, draft.SwitchCount, draft.LastUpdated, draft.ExpiresAt);
    }

    public async Task SaveDraftAsync(SaveDraftRequest request, CancellationToken ct = default)
    {
        var existing = await _repo.GetByAppointmentIdAsync(request.AppointmentId, ct);
        if (existing is null)
        {
            var draft = IntakeDraft.Create(
                request.AppointmentId,
                request.PatientId,
                request.Mode,
                request.DataJson,
                request.SwitchCount);
            await _repo.SaveAsync(draft, ct);
        }
        else
        {
            existing.Update(request.Mode, request.DataJson, request.SwitchCount);
            await _repo.SaveAsync(existing, ct);
        }
    }

    public Task DeleteDraftAsync(int appointmentId, CancellationToken ct = default)
        => _repo.DeleteByAppointmentIdAsync(appointmentId, ct);
}
