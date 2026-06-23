using System.Text.RegularExpressions;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using OpenAI;
using OpenAI.Chat;
using Polly;
using Polly.Retry;
using PropelIQ.Application.Interfaces.Repositories;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;
using PropelIQ.Domain.Enums;
using PropelIQ.Domain.ValueObjects;

namespace PropelIQ.Infrastructure.Chatbot;

public sealed class ChatbotService : IChatbotService
{
    private const int MaxMisunderstandings = 2;
    private static readonly Regex PiiSanitizePattern =
        new(@"\b\d{9}\b|\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", RegexOptions.Compiled);
    private static readonly Regex StageMarkerPattern =
        new(@"^\[STAGE:([1-6])\]\s*", RegexOptions.Compiled | RegexOptions.Multiline);

    private readonly IIntakeConversationRepository _conversationRepo;
    private readonly IChatbotPromptRepository _promptRepo;
    private readonly ChatbotOptions _options;
    private readonly ILogger<ChatbotService> _logger;
    private readonly AsyncRetryPolicy _retryPolicy;

    public ChatbotService(
        IIntakeConversationRepository conversationRepo,
        IChatbotPromptRepository promptRepo,
        IOptions<ChatbotOptions> options,
        ILogger<ChatbotService> logger)
    {
        _conversationRepo = conversationRepo;
        _promptRepo = promptRepo;
        _options = options.Value;
        _logger = logger;

        _retryPolicy = Policy
            .Handle<Exception>(ex => ex is not OperationCanceledException)
            .WaitAndRetryAsync(
                _options.MaxRetryAttempts,
                attempt => TimeSpan.FromSeconds(Math.Pow(2, attempt)),
                (ex, wait, attempt, _) =>
                    _logger.LogWarning(ex, "LLM call attempt {Attempt} failed. Retrying in {Wait}s", attempt, wait.TotalSeconds));
    }

    public async Task<StartChatResult> StartSessionAsync(StartChatRequest request, CancellationToken ct = default)
    {
        var activePrompt = await _promptRepo.GetActivePromptAsync(ct);
        var systemPromptText = activePrompt?.PromptText ?? PromptTemplates.SystemPrompt;

        var conversation = IntakeConversation.Start(request.AppointmentId, request.PatientId);
        conversation.AppendMessage(ConversationMessage.System(systemPromptText));

        var welcome = $"Hello {SanitizeName(request.PatientName)}! I'm your intake assistant. " +
                      "I'll guide you through a few quick questions before your appointment — " +
                      "it should take about 5-7 minutes. Let's get started.\n\n" +
                      PromptTemplates.ChiefComplaintPrompt;

        conversation.AppendMessage(ConversationMessage.Assistant(welcome));
        conversation.AdvanceStage(ConversationStage.ChiefComplaint);

        var conversationId = await _conversationRepo.CreateAsync(conversation, ct);
        return new StartChatResult(conversationId, welcome, (int)ConversationStage.ChiefComplaint, PromptTemplates.TotalStages);
    }

    public async Task<SendMessageResult> SendMessageAsync(SendMessageRequest request, CancellationToken ct = default)
    {
        var conversation = await _conversationRepo.GetByIdAsync(request.ConversationId, ct)
            ?? throw new InvalidOperationException($"Conversation {request.ConversationId} not found.");

        var sanitizedInput = SanitizePii(request.UserMessage);
        conversation.AppendMessage(ConversationMessage.User(sanitizedInput));

        string assistantResponse;
        try
        {
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            cts.CancelAfter(TimeSpan.FromSeconds(_options.TimeoutSeconds));

            assistantResponse = await _retryPolicy.ExecuteAsync(
                () => CallLlmAsync(conversation, cts.Token));
        }
        catch (OperationCanceledException)
        {
            _logger.LogError("LLM call timed out for conversation {Id}", request.ConversationId);
            return BuildFallbackResult(conversation, request.ConversationId, "I'm having trouble connecting right now. Please try again in a moment.");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "LLM call failed for conversation {Id}", request.ConversationId);
            return BuildFallbackResult(conversation, request.ConversationId, "Something went wrong on my end. You can continue with the standard form if you prefer.");
        }

        var isMisunderstood = IsMisunderstanding(assistantResponse);
        if (isMisunderstood)
        {
            conversation.IncrementMisunderstanding();
            assistantResponse = conversation.MisunderstandingCount >= MaxMisunderstandings
                ? PromptTemplates.FallbackPrompt
                : PromptTemplates.ClarificationPrompt;
        }
        else
        {
            var (cleanedResponse, parsedStage) = ParseStageMarker(assistantResponse);
            assistantResponse = cleanedResponse;
            if (parsedStage.HasValue)
                conversation.AdvanceStage(parsedStage.Value);
            conversation.AppendMessage(ConversationMessage.Assistant(assistantResponse));
        }

        var (extractedData, confidenceScores) = ExtractionParser.TryParse(assistantResponse);
        var isComplete = extractedData is not null;

        if (extractedData is not null && confidenceScores is not null)
        {
            conversation.UpdateExtractedData(extractedData, confidenceScores);
            conversation.MarkCompleted();
        }

        await _conversationRepo.UpdateAsync(conversation, ct);

        return new SendMessageResult(
            request.ConversationId,
            assistantResponse,
            MapExtracted(conversation.ExtractedData),
            MapScores(conversation.ConfidenceScores),
            isComplete,
            SuggestManualFallback: conversation.MisunderstandingCount >= MaxMisunderstandings,
            CurrentStage: (int)conversation.CurrentStage,
            TotalStages: PromptTemplates.TotalStages
        );
    }

    public async Task<ConversationHistoryResult> GetHistoryAsync(int conversationId, CancellationToken ct = default)
    {
        var conversation = await _conversationRepo.GetByIdAsync(conversationId, ct)
            ?? throw new InvalidOperationException($"Conversation {conversationId} not found.");

        var transcript = conversation.Transcript
            .Where(m => m.Role != "system")
            .Select(m => new MessageDto(m.Role, m.Content, m.Timestamp))
            .ToList();

        return new ConversationHistoryResult(
            conversation.Id,
            conversation.AppointmentId,
            conversation.Mode.ToString().ToLowerInvariant(),
            transcript,
            MapExtracted(conversation.ExtractedData),
            MapScores(conversation.ConfidenceScores),
            conversation.CompletedAt.HasValue
        );
    }

    private async Task<string> CallLlmAsync(IntakeConversation conversation, CancellationToken ct)
    {
        var client = new OpenAIClient(_options.ApiKey);
        var chatClient = client.GetChatClient(_options.DeploymentName);

        var history = conversation.GetTruncatedHistory(_options.MaxContextTokens);
        var messages = history.Select<ConversationMessage, ChatMessage>(m => m.Role switch
        {
            "system" => ChatMessage.CreateSystemMessage(m.Content),
            "assistant" => ChatMessage.CreateAssistantMessage(m.Content),
            _ => ChatMessage.CreateUserMessage(m.Content)
        }).ToList();

        var completionOptions = new ChatCompletionOptions
        {
            MaxOutputTokenCount = _options.MaxResponseTokens,
            Temperature = 0.4f
        };

        var completion = await chatClient.CompleteChatAsync(messages, completionOptions, ct);
        return completion.Value.Content[0].Text;
    }

    private static bool IsMisunderstanding(string response)
        => response.Contains("[MISUNDERSTOOD]", StringComparison.OrdinalIgnoreCase);

    private static (string CleanedResponse, ConversationStage? Stage) ParseStageMarker(string response)
    {
        var match = StageMarkerPattern.Match(response);
        if (!match.Success) return (response, null);

        var stage = (ConversationStage)int.Parse(match.Groups[1].Value);
        var cleaned = StageMarkerPattern.Replace(response, string.Empty).TrimStart('\r', '\n', ' ');
        return (cleaned, stage);
    }

    private static SendMessageResult BuildFallbackResult(
        IntakeConversation conversation, int conversationId, string message)
        => new(
            conversationId,
            message,
            MapExtracted(conversation.ExtractedData),
            MapScores(conversation.ConfidenceScores),
            IsComplete: false,
            SuggestManualFallback: true,
            CurrentStage: (int)conversation.CurrentStage,
            TotalStages: PromptTemplates.TotalStages
        );

    private static string SanitizeName(string name)
        => string.Join(" ", name.Split(' ').Select(part =>
            part.Length > 0 ? char.ToUpper(part[0]) + part[1..].ToLower() : part));

    private static string SanitizePii(string input)
        => PiiSanitizePattern.Replace(input, "[REDACTED]");

    private static ExtractedIntakeDataDto MapExtracted(ExtractedIntakeData data)
        => new(
            data.ChiefComplaint,
            data.MedicalHistory,
            data.Medications.Select(m => new MedicationEntryDto(m.Name, m.Dosage, m.Frequency)).ToList(),
            data.Allergies.Select(a => new AllergyEntryDto(a.Allergen, a.Reaction, a.Type.ToString())).ToList(),
            data.InsuranceInfo is { } ins ? new InsuranceInfoDto(ins.Provider, ins.MemberId, ins.GroupNumber, ins.PlanName) : null
        );

    private static ConfidenceScoresDto MapScores(ConfidenceScores scores)
        => new(scores.ChiefComplaint, scores.MedicalHistory, scores.Medications, scores.Allergies, scores.InsuranceInfo);
}
