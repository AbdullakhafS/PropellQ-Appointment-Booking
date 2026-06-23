using Microsoft.EntityFrameworkCore;
using PropelIQ.Application.Interfaces.Repositories;
using PropelIQ.Domain.Entities;
using PropelIQ.Infrastructure.Data;

namespace PropelIQ.Infrastructure.Repositories;

public sealed class IntakeDraftRepository : IIntakeDraftRepository
{
    private readonly AppDbContext _db;

    public IntakeDraftRepository(AppDbContext db) => _db = db;

    public async Task<IntakeDraft?> GetByAppointmentIdAsync(int appointmentId, CancellationToken ct = default)
        => await _db.IntakeDrafts
            .Where(d => d.AppointmentId == appointmentId)
            .FirstOrDefaultAsync(ct);

    public async Task SaveAsync(IntakeDraft draft, CancellationToken ct = default)
    {
        var existing = await GetByAppointmentIdAsync(draft.AppointmentId, ct);
        if (existing is null)
            _db.IntakeDrafts.Add(draft);
        else
        {
            existing.Update(draft.Mode, draft.DataJson, draft.SwitchCount);
            _db.IntakeDrafts.Update(existing);
        }
        await _db.SaveChangesAsync(ct);
    }

    public async Task DeleteByAppointmentIdAsync(int appointmentId, CancellationToken ct = default)
    {
        var draft = await GetByAppointmentIdAsync(appointmentId, ct);
        if (draft is not null)
        {
            _db.IntakeDrafts.Remove(draft);
            await _db.SaveChangesAsync(ct);
        }
    }
}
