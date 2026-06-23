using PropelIQ.Application.Models;

namespace PropelIQ.Application.Interfaces.Services;

public interface IInsuranceReviewService
{
    Task<PendingInsuranceResult> GetPendingAsync(PendingInsuranceQuery query, CancellationToken ct = default);

    Task<VerifyInsuranceResult> VerifyAsync(VerifyInsuranceRequest request, CancellationToken ct = default);

    Task<IReadOnlyList<VerifyInsuranceResult>> VerifyBatchAsync(
        IReadOnlyList<VerifyInsuranceRequest> requests, CancellationToken ct = default);

    Task<IReadOnlyList<AuditEntry>> GetAuditHistoryAsync(int insuranceVerificationId, CancellationToken ct = default);
}
