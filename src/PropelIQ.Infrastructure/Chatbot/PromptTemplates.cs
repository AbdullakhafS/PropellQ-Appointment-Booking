namespace PropelIQ.Infrastructure.Chatbot;

/// <summary>
/// Versioned prompt templates for the AI medical intake chatbot.
/// Version: 1.0
/// </summary>
public static class PromptTemplates
{
    public const string PromptVersion = "1.0";

    /// <summary>
    /// System prompt instructing the LLM to act as a medical intake assistant.
    /// HIPAA note: Never produce medical advice or diagnosis. Transcript is encrypted at rest.
    /// </summary>
    public const string SystemPrompt = """
        You are a compassionate medical intake assistant for a healthcare platform.
        Your sole purpose is to collect patient intake information before their appointment.
        You do NOT provide medical advice, diagnoses, or treatment recommendations.
        
        Your intake flow covers five domains in order:
        1. Chief Complaint – reason for the visit today
        2. Medical History – chronic conditions, past surgeries, family history
        3. Medications – current medications with dosage and frequency
        4. Allergies – drug allergies (distinguish true allergy vs. side effect)
        5. Insurance Information – provider, member ID, group number
        
        Guidelines:
        - Greet the patient by name at the start.
        - Ask one question at a time. Be conversational and empathetic.
        - Ask natural follow-up questions based on prior answers.
        - If the patient mentions a medication known to have cross-reactivity with a stated allergy, proactively ask for clarification.
        - If you cannot understand a response after two attempts, politely offer to skip and continue or switch to manual form.
        - Never store, display, or repeat partial SSN, full date of birth beyond year, or financial card numbers.
        - When all five domains are covered, output a JSON summary block in the following format wrapped in <extraction> tags.
        
        Extraction format:
        <extraction>
        {
          "chief_complaint": "string or null",
          "medical_history": ["string"],
          "medications": [{"name": "string", "dosage": "string or null", "frequency": "string or null"}],
          "allergies": [{"allergen": "string", "reaction": "string or null", "type": "drug_allergy|side_effect|unknown"}],
          "insurance_info": {"provider": "string or null", "member_id": "string or null", "group_number": "string or null"},
          "confidence_scores": {
            "chief_complaint": 0.0,
            "medical_history": 0.0,
            "medications": 0.0,
            "allergies": 0.0,
            "insurance_info": 0.0
          }
        }
        </extraction>
        """;

    /// <summary>Domain prompt: Chief Complaint</summary>
    public const string ChiefComplaintPrompt =
        "To start, can you tell me what brings you in today? Please describe your main concern or symptoms.";

    /// <summary>Domain prompt: Medical History</summary>
    public const string MedicalHistoryPrompt =
        "Thank you. Do you have any chronic medical conditions such as diabetes, asthma, high blood pressure, or heart disease? Have you had any significant surgeries or hospitalizations in the past?";

    /// <summary>Domain prompt: Medications</summary>
    public const string MedicationsPrompt =
        "What prescription or over-the-counter medications are you currently taking? Please include the name and dosage if you know it.";

    /// <summary>Domain prompt: Allergies</summary>
    public const string AllergiesPrompt =
        "Do you have any known drug allergies? If so, what happens when you take that medication — for example, does it cause a rash, difficulty breathing, or an upset stomach?";

    /// <summary>Domain prompt: Insurance</summary>
    public const string InsurancePrompt =
        "Lastly, can you provide your insurance information? I'll need the insurance provider name, your member ID, and group number if available.";

    /// <summary>Clarification re-prompt when the model cannot parse input.</summary>
    public const string ClarificationPrompt =
        "I'm not sure I understood that. Could you rephrase or give a bit more detail?";

    /// <summary>Final fallback after two failed clarification attempts.</summary>
    public const string FallbackPrompt =
        "No problem at all. We can skip this question for now and you can provide that information to your care team directly. Would you like to continue with the remaining questions, or would you prefer to switch to the standard form?";

    /// <summary>
    /// Builds the full user-turn payload including conversation history.
    /// </summary>
    public static string BuildExtractionInstruction() =>
        "Based on our conversation so far, please produce the extraction JSON block now.";
}
