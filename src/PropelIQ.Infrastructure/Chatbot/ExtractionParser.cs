using System.Text.Json;
using System.Text.Json.Serialization;
using PropelIQ.Domain.ValueObjects;

namespace PropelIQ.Infrastructure.Chatbot;

public static class ExtractionParser
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    public static (ExtractedIntakeData? data, ConfidenceScores? scores) TryParse(string assistantResponse)
    {
        var start = assistantResponse.IndexOf("<extraction>", StringComparison.OrdinalIgnoreCase);
        var end = assistantResponse.IndexOf("</extraction>", StringComparison.OrdinalIgnoreCase);

        if (start < 0 || end < 0 || end <= start)
            return (null, null);

        var json = assistantResponse[(start + "<extraction>".Length)..end].Trim();

        try
        {
            var raw = JsonSerializer.Deserialize<ExtractionPayload>(json, JsonOptions);
            if (raw is null) return (null, null);

            var medications = (raw.Medications ?? [])
                .Select(m => new MedicationEntry(m.Name ?? string.Empty, m.Dosage, m.Frequency))
                .ToList();

            var allergies = (raw.Allergies ?? [])
                .Select(a => new AllergyEntry(
                    a.Allergen ?? string.Empty,
                    a.Reaction,
                    ParseAllergyType(a.Type)))
                .ToList();

            InsuranceInfo? insurance = raw.InsuranceInfo is { } ins
                ? new InsuranceInfo(ins.Provider, ins.MemberId, ins.GroupNumber, ins.PlanName)
                : null;

            var data = new ExtractedIntakeData(
                raw.ChiefComplaint,
                raw.MedicalHistory ?? [],
                medications,
                allergies,
                insurance
            );

            var cs = raw.ConfidenceScores;
            var scores = cs is not null
                ? new ConfidenceScores(cs.ChiefComplaint, cs.MedicalHistory, cs.Medications, cs.Allergies, cs.InsuranceInfo)
                : ConfidenceScores.Zero();

            return (data, scores);
        }
        catch (JsonException)
        {
            return (null, null);
        }
    }

    private static AllergyType ParseAllergyType(string? raw) => raw?.ToLowerInvariant() switch
    {
        "drug_allergy" => AllergyType.DrugAllergy,
        "side_effect" => AllergyType.SideEffect,
        _ => AllergyType.Unknown
    };

    // --- Internal deserialization contracts ---

    private sealed class ExtractionPayload
    {
        [JsonPropertyName("chief_complaint")] public string? ChiefComplaint { get; init; }
        [JsonPropertyName("medical_history")] public List<string>? MedicalHistory { get; init; }
        [JsonPropertyName("medications")] public List<MedRaw>? Medications { get; init; }
        [JsonPropertyName("allergies")] public List<AllergyRaw>? Allergies { get; init; }
        [JsonPropertyName("insurance_info")] public InsuranceRaw? InsuranceInfo { get; init; }
        [JsonPropertyName("confidence_scores")] public ConfidenceRaw? ConfidenceScores { get; init; }
    }

    private sealed class MedRaw
    {
        [JsonPropertyName("name")] public string? Name { get; init; }
        [JsonPropertyName("dosage")] public string? Dosage { get; init; }
        [JsonPropertyName("frequency")] public string? Frequency { get; init; }
    }

    private sealed class AllergyRaw
    {
        [JsonPropertyName("allergen")] public string? Allergen { get; init; }
        [JsonPropertyName("reaction")] public string? Reaction { get; init; }
        [JsonPropertyName("type")] public string? Type { get; init; }
    }

    private sealed class InsuranceRaw
    {
        [JsonPropertyName("provider")] public string? Provider { get; init; }
        [JsonPropertyName("member_id")] public string? MemberId { get; init; }
        [JsonPropertyName("group_number")] public string? GroupNumber { get; init; }
        [JsonPropertyName("plan_name")] public string? PlanName { get; init; }
    }

    private sealed class ConfidenceRaw
    {
        [JsonPropertyName("chief_complaint")] public double ChiefComplaint { get; init; }
        [JsonPropertyName("medical_history")] public double MedicalHistory { get; init; }
        [JsonPropertyName("medications")] public double Medications { get; init; }
        [JsonPropertyName("allergies")] public double Allergies { get; init; }
        [JsonPropertyName("insurance_info")] public double InsuranceInfo { get; init; }
    }
}
