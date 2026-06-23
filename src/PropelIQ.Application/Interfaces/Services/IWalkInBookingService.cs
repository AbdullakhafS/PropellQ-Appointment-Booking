using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

public interface IWalkInBookingService
{
    /// <summary>Searches patients by name, phone, email, or patient ID substring.</summary>
    Task<IReadOnlyList<PatientSummary>> SearchPatientsAsync(PatientSearchQuery query, CancellationToken ct = default);

    /// <summary>Creates a new patient record for walk-in registration.</summary>
    Task<PatientSummary> CreatePatientAsync(CreatePatientRequest request, CancellationToken ct = default);

    /// <summary>Books a walk-in appointment; always sets IsWalkIn = true.</summary>
    Task<BookWalkInResult> BookWalkInAsync(BookWalkInRequest request, CancellationToken ct = default);
}
