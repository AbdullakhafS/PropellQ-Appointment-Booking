using PropelIQ.Domain.Entities;

namespace PropelIQ.Application.Interfaces.Repositories;

public interface IChatbotPromptRepository
{
    Task<ChatbotPrompt?> GetActivePromptAsync(CancellationToken ct = default);
    Task<ChatbotPrompt?> GetByVersionAsync(string version, CancellationToken ct = default);
    Task CreateAsync(ChatbotPrompt prompt, CancellationToken ct = default);
}
