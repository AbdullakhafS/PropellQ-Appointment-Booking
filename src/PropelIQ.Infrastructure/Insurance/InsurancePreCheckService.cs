using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;
using PropelIQ.Infrastructure.Data;

namespace PropelIQ.Infrastructure.Insurance;

public sealed class InsurancePreCheckService : IInsurancePreCheckService
{
    private readonly AppDbContext _db;
    private readonly ILogger<InsurancePreCheckService> _logger;

    public InsurancePreCheckService(AppDbContext db, ILogger<InsurancePreCheckService> logger)
    {
        _db = db;
        _logger = logger;
    }

    public async Task<InsurancePreCheckResult> CheckAsync(
        InsurancePreCheckRequest request,
        CancellationToken ct = default)
    {
        try
        {
            var plans = await _db.InsurancePlans.AsNoTracking().ToListAsync(ct);

            var match = InsuranceMatcher.Evaluate(
                request.InsuranceName,
                request.MemberId,
                request.GroupNumber,
                plans);

            var record = InsuranceVerification.Create(
                request.AppointmentId,
                request.PatientId,
                request.InsuranceName,
                request.MemberId,
                request.GroupNumber,
                match.MatchedPlan?.Id,
                match.ConfidenceScore,
                match.VerificationStatus,
                match.Reason);

            _db.InsuranceVerifications.Add(record);
            await _db.SaveChangesAsync(ct);

            _logger.LogInformation(
                "Insurance pre-check: appointment={AppointmentId} plan={Plan} confidence={Score} status={Status}",
                request.AppointmentId, match.MatchedPlan?.Name ?? "unknown",
                match.ConfidenceScore, match.VerificationStatus);

            return new InsurancePreCheckResult(
                match.MatchedPlan?.Id,
                match.MatchedPlan?.Name,
                match.ConfidenceScore,
                match.VerificationStatus,
                match.Reason);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "Insurance pre-check failed for appointment {AppointmentId}. Allowing booking to proceed.",
                request.AppointmentId);

            // Soft failure: return an unverified result so intake can still complete
            return new InsurancePreCheckResult(
                null, null, 0, "unverified",
                "Insurance check could not be completed. Manual review required.");
        }
    }
}
