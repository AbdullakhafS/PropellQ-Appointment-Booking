using Microsoft.EntityFrameworkCore;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;
using PropelIQ.Infrastructure.Data;

namespace PropelIQ.Infrastructure.Insurance;

public sealed class InsuranceReviewService : IInsuranceReviewService
{
    private readonly AppDbContext _db;

    public InsuranceReviewService(AppDbContext db) => _db = db;

    public async Task<PendingInsuranceResult> GetPendingAsync(
        PendingInsuranceQuery query, CancellationToken ct = default)
    {
        var cutoff = query.DateRangeDays.HasValue
            ? DateTimeOffset.UtcNow.AddDays(query.DateRangeDays.Value)
            : (DateTimeOffset?)null;

        var q = _db.InsuranceVerifications.AsNoTracking();

        if (!string.IsNullOrWhiteSpace(query.Status))
            q = q.Where(v => v.VerificationStatus == query.Status);

        if (!string.IsNullOrWhiteSpace(query.InsuranceName))
            q = q.Where(v => v.ProvidedInsuranceName != null &&
                             v.ProvidedInsuranceName.Contains(query.InsuranceName));

        // Apply sort before loading for server-side pagination
        q = query.SortBy.ToLowerInvariant() switch
        {
            "confidence" => query.SortAscending
                ? q.OrderBy(v => v.ConfidenceScore)
                : q.OrderByDescending(v => v.ConfidenceScore),
            "insurance" => query.SortAscending
                ? q.OrderBy(v => v.ProvidedInsuranceName)
                : q.OrderByDescending(v => v.ProvidedInsuranceName),
            _ => query.SortAscending   // default: created_at asc (appointment date proxy)
                ? q.OrderBy(v => v.CreatedAt)
                : q.OrderByDescending(v => v.CreatedAt)
        };

        var total = await q.CountAsync(ct);

        var rows = await q
            .Skip((query.Page - 1) * query.PageSize)
            .Take(query.PageSize)
            .Join(_db.InsurancePlans,
                v => v.MatchedPlanId,
                p => p.Id,
                (v, p) => new { v, PlanName = p.Name })
            .Select(x => new PendingInsuranceRow(
                x.v.Id,
                x.v.AppointmentId,
                x.v.PatientId,
                null,   // Patient name: not stored on verification — UI can enrich if needed
                x.v.ProvidedInsuranceName,
                x.v.ProvidedMemberId,
                x.v.MatchedPlanId,
                x.PlanName,
                x.v.ConfidenceScore,
                x.v.VerificationStatus,
                null,   // AppointmentDate: not denormalised — placeholder
                x.v.VerifiedAt,
                x.v.CreatedAt))
            .ToListAsync(ct);

        // Also fetch rows with no matched plan (left join equivalent with fallback)
        var unmatched = await q
            .Where(v => v.MatchedPlanId == null)
            .Skip((query.Page - 1) * query.PageSize)
            .Take(query.PageSize)
            .Select(v => new PendingInsuranceRow(
                v.Id, v.AppointmentId, v.PatientId, null,
                v.ProvidedInsuranceName, v.ProvidedMemberId,
                null, null,
                v.ConfidenceScore, v.VerificationStatus,
                null, v.VerifiedAt, v.CreatedAt))
            .ToListAsync(ct);

        // Merge (matched overrides unmatched by Id)
        var allIds = new HashSet<int>(rows.Select(r => r.Id));
        var merged = rows.Concat(unmatched.Where(u => !allIds.Contains(u.Id))).ToList();

        return new PendingInsuranceResult(merged, total, query.Page, query.PageSize);
    }

    public async Task<VerifyInsuranceResult> VerifyAsync(
        VerifyInsuranceRequest request, CancellationToken ct = default)
    {
        var record = await _db.InsuranceVerifications.FindAsync([request.InsuranceVerificationId], ct)
            ?? throw new InvalidOperationException($"InsuranceVerification {request.InsuranceVerificationId} not found.");

        var previousStatus = record.VerificationStatus;

        record.StaffVerify(request.StaffId, request.NewStatus, request.VerificationMethod, request.Notes);

        var audit = InsuranceVerificationAudit.Create(
            request.InsuranceVerificationId,
            previousStatus,
            request.NewStatus,
            request.StaffId,
            request.VerificationMethod,
            request.Notes);

        _db.InsuranceVerificationAudits.Add(audit);
        await _db.SaveChangesAsync(ct);

        return new VerifyInsuranceResult(record.Id, record.VerificationStatus, request.StaffId, record.VerifiedAt!.Value);
    }

    public async Task<IReadOnlyList<VerifyInsuranceResult>> VerifyBatchAsync(
        IReadOnlyList<VerifyInsuranceRequest> requests, CancellationToken ct = default)
    {
        var results = new List<VerifyInsuranceResult>();

        foreach (var req in requests)
        {
            try { results.Add(await VerifyAsync(req, ct)); }
            catch (InvalidOperationException) { /* record not found — skip */ }
        }

        return results;
    }

    public async Task<IReadOnlyList<AuditEntry>> GetAuditHistoryAsync(
        int insuranceVerificationId, CancellationToken ct = default)
    {
        return await _db.InsuranceVerificationAudits
            .AsNoTracking()
            .Where(a => a.InsuranceVerificationId == insuranceVerificationId)
            .OrderByDescending(a => a.VerifiedAt)
            .Select(a => new AuditEntry(
                a.Id,
                a.PreviousStatus,
                a.NewStatus,
                a.VerifiedByStaffId,
                a.VerificationMethod,
                a.Notes,
                a.VerifiedAt))
            .ToListAsync(ct);
    }
}
