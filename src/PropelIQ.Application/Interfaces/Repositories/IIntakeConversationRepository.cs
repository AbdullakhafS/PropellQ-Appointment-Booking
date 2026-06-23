using PropelIQ.Domain.Entities;

namespace PropelIQ.Application.Interfaces.Repositories;

public interface IIntakeConversationRepository
{
    Task<IntakeConversation?> GetByIdAsync(int conversationId, CancellationToken ct = default);
    Task<IntakeConversation?> GetByAppointmentIdAsync(int appointmentId, CancellationToken ct = default);
    Task<IntakeConversation?> GetLastCompletedByPatientIdAsync(int patientId, CancellationToken ct = default);
    Task<int> CreateAsync(IntakeConversation conversation, CancellationToken ct = default);
    Task UpdateAsync(IntakeConversation conversation, CancellationToken ct = default);
}
