using Microsoft.EntityFrameworkCore;
using PropelIQ.Application.Interfaces.Repositories;
using PropelIQ.Domain.Entities;
using PropelIQ.Infrastructure.Data;

namespace PropelIQ.Infrastructure.Repositories;

public sealed class ChatbotPromptRepository : IChatbotPromptRepository
{
    private readonly AppDbContext _db;

    public ChatbotPromptRepository(AppDbContext db) => _db = db;

    public async Task<ChatbotPrompt?> GetActivePromptAsync(CancellationToken ct = default)
        => await _db.ChatbotPrompts
            .Where(p => p.DeprecatedAt == null)
            .OrderByDescending(p => p.EffectiveDate)
            .FirstOrDefaultAsync(ct);

    public async Task<ChatbotPrompt?> GetByVersionAsync(string version, CancellationToken ct = default)
        => await _db.ChatbotPrompts
            .FirstOrDefaultAsync(p => p.PromptVersion == version, ct);

    public async Task CreateAsync(ChatbotPrompt prompt, CancellationToken ct = default)
    {
        _db.ChatbotPrompts.Add(prompt);
        await _db.SaveChangesAsync(ct);
    }
}
