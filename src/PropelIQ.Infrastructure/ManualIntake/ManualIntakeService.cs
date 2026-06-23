using PropelIQ.Application.Interfaces.Repositories;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;
using PropelIQ.Domain.ValueObjects;

namespace PropelIQ.Infrastructure.ManualIntake;

public sealed class ManualIntakeService : IManualIntakeService
{
    private readonly IIntakeConversationRepository _repo;

    public ManualIntakeService(IIntakeConversationRepository repo) => _repo = repo;

    public async Task<LastIntakeResult?> GetLastIntakeAsync(int patientId, CancellationToken ct = default)
    {
        var last = await _repo.GetLastCompletedByPatientIdAsync(patientId, ct);
        if (last is null) return null;

        var d = last.ExtractedData;

        // Extract "other conditions" text — stored as the last entry if it has the Other: prefix
        string? other = null;
        var conditions = d.MedicalHistory.ToList();
        if (conditions.Count > 0 && conditions[^1].StartsWith("Other: ", StringComparison.OrdinalIgnoreCase))
        {
            other = conditions[^1]["Other: ".Length..];
            conditions.RemoveAt(conditions.Count - 1);
        }

        return new LastIntakeResult(
            d.ChiefComplaint,
            conditions,
            other,
            d.Medications.Select(m => new MedicationEntryDto(m.Name, m.Dosage, m.Frequency)).ToList(),
            d.Allergies.Select(a => new AllergyEntryDto(a.Allergen, a.Reaction, a.Type.ToString())).ToList(),
            d.InsuranceInfo is { } ins ? new InsuranceInfoDto(ins.Provider, ins.MemberId, ins.GroupNumber, ins.PlanName) : null,
            last.CompletedAt ?? last.CreatedAt
        );
    }

    public async Task<SubmitManualIntakeResult> SubmitAsync(SubmitManualIntakeRequest request, CancellationToken ct = default)
    {
        var conversation = IntakeConversation.StartManual(request.AppointmentId, request.PatientId);

        // Combine structured conditions with free-text "Other"
        var history = new List<string>(request.MedicalHistory);
        if (!string.IsNullOrWhiteSpace(request.OtherConditions))
            history.Add($"Other: {request.OtherConditions.Trim()}");

        var medications = request.Medications
            .Where(m => !string.IsNullOrWhiteSpace(m.Name))
            .Select(m => new MedicationEntry(m.Name, m.Dosage, m.Frequency))
            .ToList();

        var allergies = request.Allergies
            .Where(a => !string.IsNullOrWhiteSpace(a.Allergen))
            .Select(a => new AllergyEntry(
                a.Allergen,
                a.Reaction,
                Enum.TryParse<AllergyType>(a.Type, ignoreCase: true, out var t) ? t : AllergyType.Unknown))
            .ToList();

        InsuranceInfo? insurance = request.InsuranceInfo is { Provider: not null } or { MemberId: not null }
            ? new InsuranceInfo(
                request.InsuranceInfo.Provider,
                request.InsuranceInfo.MemberId,
                request.InsuranceInfo.GroupNumber,
                request.InsuranceInfo.PlanName)
            : null;

        var data = new ExtractedIntakeData(
            request.ChiefComplaint,
            history,
            medications,
            allergies,
            insurance
        );

        conversation.UpdateExtractedData(data, ConfidenceScores.Zero());
        conversation.MarkCompleted();

        var id = await _repo.CreateAsync(conversation, ct);
        return new SubmitManualIntakeResult(id);
    }
}
