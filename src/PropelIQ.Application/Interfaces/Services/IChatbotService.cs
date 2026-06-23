using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

public interface IChatbotService
{
    Task<StartChatResult> StartSessionAsync(StartChatRequest request, CancellationToken ct = default);
    Task<SendMessageResult> SendMessageAsync(SendMessageRequest request, CancellationToken ct = default);
    Task<ConversationHistoryResult> GetHistoryAsync(int conversationId, CancellationToken ct = default);
}
