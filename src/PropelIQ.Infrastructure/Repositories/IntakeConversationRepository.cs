using Microsoft.EntityFrameworkCore;
using PropelIQ.Application.Interfaces.Repositories;
using PropelIQ.Domain.Entities;
using PropelIQ.Infrastructure.Data;

namespace PropelIQ.Infrastructure.Repositories;

public sealed class IntakeConversationRepository : IIntakeConversationRepository
{
    private readonly AppDbContext _db;

    public IntakeConversationRepository(AppDbContext db) => _db = db;

    public async Task<IntakeConversation?> GetByIdAsync(int conversationId, CancellationToken ct = default)
        => await _db.IntakeConversations.FindAsync([conversationId], ct);

    public async Task<IntakeConversation?> GetByAppointmentIdAsync(int appointmentId, CancellationToken ct = default)
        => await _db.IntakeConversations
            .Where(c => c.AppointmentId == appointmentId)
            .OrderByDescending(c => c.CreatedAt)
            .FirstOrDefaultAsync(ct);

    public async Task<int> CreateAsync(IntakeConversation conversation, CancellationToken ct = default)
    {
        _db.IntakeConversations.Add(conversation);
        await _db.SaveChangesAsync(ct);
        return conversation.Id;
    }

    public async Task UpdateAsync(IntakeConversation conversation, CancellationToken ct = default)
    {
        _db.IntakeConversations.Update(conversation);
        await _db.SaveChangesAsync(ct);
    }
}
