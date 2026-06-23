namespace PropelIQ.Domain.Enums;

/// <summary>
/// Tracks which intake stage the AI chatbot conversation is currently in.
/// Stages map directly to the progress indicator shown to the patient (Step 1–6).
/// </summary>
public enum ConversationStage
{
    Greeting = 0,
    ChiefComplaint = 1,
    MedicalHistory = 2,
    Medications = 3,
    Allergies = 4,
    Insurance = 5,
    Summary = 6
}
