using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

public interface IAppointmentDetailService
{
    /// <summary>Returns the full appointment detail with status history. Null if not found.</summary>
    AppointmentDetail? GetDetail(Guid appointmentId);

    /// <summary>Returns the ordered status-transition history for an appointment.</summary>
    IReadOnlyList<AppointmentHistoryEntry> GetHistory(Guid appointmentId);

    /// <summary>Records a status transition in the history log.</summary>
    void RecordTransition(Guid appointmentId, string previousStatus, string newStatus, string? notes = null);
}
