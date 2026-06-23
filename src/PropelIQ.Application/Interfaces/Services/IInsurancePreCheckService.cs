using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

public interface IInsurancePreCheckService
{
    /// <summary>
    /// Performs a soft insurance pre-check, persists the audit record, and returns the result.
    /// Never throws; always returns a result (confidence 0 / unverified on any failure).
    /// </summary>
    Task<InsurancePreCheckResult> CheckAsync(InsurancePreCheckRequest request, CancellationToken ct = default);
}
