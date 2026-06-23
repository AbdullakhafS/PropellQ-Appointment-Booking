using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.DTOs.Common;
using PropelIQ.Api.DTOs.Intake;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/intake/chat")]
[Produces("application/json")]
public sealed class ChatbotController : ControllerBase
{
    private readonly IChatbotService _chatbotService;
    private readonly ILogger<ChatbotController> _logger;

    public ChatbotController(IChatbotService chatbotService, ILogger<ChatbotController> logger)
    {
        _chatbotService = chatbotService;
        _logger = logger;
    }

    /// <summary>
    /// Starts a new AI intake chatbot session for an appointment.
    /// </summary>
    /// <response code="200">Session started; returns conversationId and welcome message.</response>
    /// <response code="400">Validation error in request body.</response>
    [HttpPost("start")]
    [ProducesResponseType(typeof(ApiResponse<StartChatResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<StartChatResponseDto>), StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> StartChat(
        [FromBody] StartChatRequestDto request,
        CancellationToken ct)
    {
        var result = await _chatbotService.StartSessionAsync(
            new StartChatRequest(request.AppointmentId, request.PatientId, request.PatientName),
            ct);

        return Ok(ApiResponse<StartChatResponseDto>.Ok(
            new StartChatResponseDto(result.ConversationId, result.WelcomeMessage)));
    }

    /// <summary>
    /// Sends a patient message and receives an AI assistant response.
    /// </summary>
    /// <response code="200">Assistant response returned with current extracted data.</response>
    /// <response code="400">Validation error.</response>
    /// <response code="404">Conversation not found.</response>
    [HttpPost("message")]
    [ProducesResponseType(typeof(ApiResponse<SendMessageResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<SendMessageResponseDto>), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> SendMessage(
        [FromBody] SendMessageRequestDto request,
        CancellationToken ct)
    {
        try
        {
            var result = await _chatbotService.SendMessageAsync(
                new SendMessageRequest(request.ConversationId, request.AppointmentId, request.UserMessage),
                ct);

            return Ok(ApiResponse<SendMessageResponseDto>.Ok(MapSendResult(result)));
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogWarning(ex, "Conversation {Id} not found", request.ConversationId);
            return NotFound();
        }
    }

    /// <summary>
    /// Retrieves the full conversation history for a given conversationId.
    /// </summary>
    /// <response code="200">Conversation transcript and extracted data.</response>
    /// <response code="404">Conversation not found.</response>
    [HttpGet("{conversationId:int}")]
    [ProducesResponseType(typeof(ApiResponse<ConversationHistoryResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetHistory(int conversationId, CancellationToken ct)
    {
        try
        {
            var result = await _chatbotService.GetHistoryAsync(conversationId, ct);

            var dto = new ConversationHistoryResponseDto(
                result.ConversationId,
                result.AppointmentId,
                result.Mode,
                result.Transcript.Select(m => new MessageResponseDto(m.Role, m.Content, m.Timestamp)).ToList(),
                MapExtracted(result.ExtractedData),
                MapScores(result.ConfidenceScores),
                result.IsComplete);

            return Ok(ApiResponse<ConversationHistoryResponseDto>.Ok(dto));
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogWarning(ex, "Conversation {Id} not found", conversationId);
            return NotFound();
        }
    }

    private static SendMessageResponseDto MapSendResult(SendMessageResult r)
        => new(
            r.ConversationId,
            r.AssistantMessage,
            MapExtracted(r.ExtractedData),
            MapScores(r.ConfidenceScores),
            r.IsComplete,
            r.SuggestManualFallback);

    private static ExtractedDataDto MapExtracted(ExtractedIntakeDataDto d)
        => new(
            d.ChiefComplaint,
            d.MedicalHistory,
            d.Medications.Select(m => new MedicationDto(m.Name, m.Dosage, m.Frequency)).ToList(),
            d.Allergies.Select(a => new AllergyDto(a.Allergen, a.Reaction, a.Type)).ToList(),
            d.InsuranceInfo is { } ins ? new InsuranceInfoDto(ins.Provider, ins.MemberId, ins.GroupNumber) : null);

    private static ConfidenceScoresResponseDto MapScores(ConfidenceScoresDto s)
        => new(s.ChiefComplaint, s.MedicalHistory, s.Medications, s.Allergies, s.InsuranceInfo);
}
