using PropelIQ.Domain.ValueObjects;
using Xunit;

namespace PropelIQ.Tests.Services;

public sealed class ExtractionParserTests
{
    [Fact]
    public void TryParse_ValidExtractionBlock_ReturnsExtractedData()
    {
        var response = """
            Thank you for sharing that information!
            <extraction>
            {
              "chief_complaint": "persistent cough for 3 days",
              "medical_history": ["asthma", "hypertension"],
              "medications": [
                {"name": "metformin", "dosage": "500mg", "frequency": "twice daily"},
                {"name": "lisinopril", "dosage": "10mg", "frequency": "once daily"}
              ],
              "allergies": [
                {"allergen": "penicillin", "reaction": "rash", "type": "drug_allergy"}
              ],
              "insurance_info": {"provider": "BlueCross", "member_id": "XYZ123", "group_number": "GRP99"},
              "confidence_scores": {
                "chief_complaint": 0.95,
                "medical_history": 0.88,
                "medications": 0.92,
                "allergies": 0.97,
                "insurance_info": 0.85
              }
            }
            </extraction>
            """;

        var (data, scores) = PropelIQ.Infrastructure.Chatbot.ExtractionParser.TryParse(response);

        Assert.NotNull(data);
        Assert.Equal("persistent cough for 3 days", data!.ChiefComplaint);
        Assert.Equal(2, data.MedicalHistory.Count);
        Assert.Equal(2, data.Medications.Count);
        Assert.Equal("metformin", data.Medications[0].Name);
        Assert.Equal("penicillin", data.Allergies[0].Allergen);
        Assert.Equal(AllergyType.DrugAllergy, data.Allergies[0].Type);
        Assert.NotNull(data.InsuranceInfo);
        Assert.Equal("BlueCross", data.InsuranceInfo!.Provider);

        Assert.NotNull(scores);
        Assert.Equal(0.95, scores!.ChiefComplaint);
    }

    [Fact]
    public void TryParse_NoExtractionBlock_ReturnsNull()
    {
        var response = "I'm not sure I understood that. Could you rephrase?";
        var (data, scores) = PropelIQ.Infrastructure.Chatbot.ExtractionParser.TryParse(response);

        Assert.Null(data);
        Assert.Null(scores);
    }

    [Fact]
    public void TryParse_MalformedJson_ReturnsNull()
    {
        var response = "<extraction>{ invalid json }</extraction>";
        var (data, scores) = PropelIQ.Infrastructure.Chatbot.ExtractionParser.TryParse(response);

        Assert.Null(data);
        Assert.Null(scores);
    }
}
