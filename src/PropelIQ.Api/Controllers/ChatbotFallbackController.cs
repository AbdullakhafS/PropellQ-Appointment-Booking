using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.DTOs.Common;
using PropelIQ.Application.Interfaces.Repositories;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/intake/chat")]
[Produces("application/json")]
public sealed class ChatbotFallbackController : ControllerBase
{
    private readonly IIntakeConversationRepository _repo;
    private readonly ILogger<ChatbotFallbackController> _logger;

    public ChatbotFallbackController(
        IIntakeConversationRepository repo,
        ILogger<ChatbotFallbackController> logger)
    {
        _repo = repo;
        _logger = logger;
    }

    /// <summary>
    /// Switches a conversation from AI mode to manual intake.
    /// Persists switched_to_manual_at and preserves all collected data.
    /// </summary>
    /// <response code="204">Successfully switched to manual mode.</response>
    /// <response code="404">Conversation not found.</response>
    [HttpPost("{conversationId:int}/switch-to-manual")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> SwitchToManual(int conversationId, CancellationToken ct)
    {
        var conversation = await _repo.GetByIdAsync(conversationId, ct);
        if (conversation is null)
        {
            _logger.LogWarning("Conversation {Id} not found for manual switch", conversationId);
            return NotFound();
        }

        conversation.SwitchToManual();
        await _repo.UpdateAsync(conversation, ct);

        _logger.LogInformation(
            "Conversation {Id} switched to manual intake at {Time}",
            conversationId,
            conversation.SwitchedToManualAt);

        return NoContent();
    }
}
