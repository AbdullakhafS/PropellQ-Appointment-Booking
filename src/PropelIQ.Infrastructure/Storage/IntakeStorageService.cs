using Microsoft.EntityFrameworkCore;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;
using PropelIQ.Domain.Entities;
using PropelIQ.Infrastructure.Data;

namespace PropelIQ.Infrastructure.Storage;

public sealed class IntakeStorageService : IIntakeStorageService
{
    private readonly AppDbContext _db;

    public IntakeStorageService(AppDbContext db) => _db = db;

    public async Task<StoreIntakeResult> StoreAsync(StoreIntakeRequest request, CancellationToken ct = default)
    {
        await using var tx = await _db.Database.BeginTransactionAsync(ct);

        var intake = IntakeResponse.Create(
            request.AppointmentId,
            request.PatientId,
            request.Mode,
            request.ChiefComplaint,
            request.Notes,
            request.CreatedByStaffId);

        _db.IntakeResponses.Add(intake);
        await _db.SaveChangesAsync(ct); // get generated Id

        // Medical history
        foreach (var h in request.MedicalHistory)
        {
            _db.IntakeMedicalHistories.Add(
                IntakeMedicalHistory.Create(intake.Id, h.ConditionName, h.ConditionCode, h.ConfidenceScore, null));
        }

        // Medications
        foreach (var m in request.Medications)
        {
            _db.IntakeMedications.Add(
                IntakeMedication.Create(intake.Id, m.MedicationName, m.Dosage, m.Frequency, m.Route, m.ConfidenceScore, null));
        }

        // Allergies
        foreach (var a in request.Allergies)
        {
            _db.IntakeAllergies.Add(
                IntakeAllergy.Create(intake.Id, a.AllergenType, a.AllergenName, a.ReactionType, a.ReactionDescription, a.Severity, a.ConfidenceScore));
        }

        // Insurance
        if (request.InsuranceInfo is { } ins)
        {
            _db.IntakeInsurances.Add(
                IntakeInsurance.Create(intake.Id, ins.InsuranceName, ins.MemberId, ins.GroupNumber, ins.PlanName,
                    request.VerificationStatus, request.InsuranceConfidenceScore));
        }

        // Audit log
        _db.IntakeAuditLogs.Add(IntakeAuditLog.Create(
            intake.Id, "create", null, null, "completed",
            request.CreatedByStaffId?.ToString() ?? request.Mode,
            null));

        await _db.SaveChangesAsync(ct);
        await tx.CommitAsync(ct);

        return new StoreIntakeResult(intake.Id, intake.AppointmentId, intake.CompletedAt);
    }

    public async Task<GetIntakeResult?> GetByAppointmentAsync(int appointmentId, CancellationToken ct = default)
    {
        var intake = await _db.IntakeResponses
            .AsNoTracking()
            .Where(r => r.AppointmentId == appointmentId && r.Status != "voided")
            .OrderByDescending(r => r.CompletedAt)
            .FirstOrDefaultAsync(ct);

        return intake is null ? null : await LoadFullAsync(intake, ct);
    }

    public async Task<IReadOnlyList<GetIntakeResult>> GetByPatientAsync(int patientId, CancellationToken ct = default)
    {
        var intakes = await _db.IntakeResponses
            .AsNoTracking()
            .Where(r => r.PatientId == patientId && r.Status != "voided")
            .OrderByDescending(r => r.CompletedAt)
            .ToListAsync(ct);

        var results = new List<GetIntakeResult>();
        foreach (var i in intakes)
            results.Add(await LoadFullAsync(i, ct));

        return results;
    }

    public async Task<GetIntakeResult?> GetLatestByPatientAsync(int patientId, CancellationToken ct = default)
    {
        var intake = await _db.IntakeResponses
            .AsNoTracking()
            .Where(r => r.PatientId == patientId && r.Status != "voided")
            .OrderByDescending(r => r.CompletedAt)
            .FirstOrDefaultAsync(ct);

        return intake is null ? null : await LoadFullAsync(intake, ct);
    }

    public async Task<GetIntakeResult> UpdateAsync(UpdateIntakeRequest request, CancellationToken ct = default)
    {
        var intake = await _db.IntakeResponses.FindAsync([request.IntakeId], ct)
            ?? throw new InvalidOperationException($"IntakeResponse {request.IntakeId} not found.");

        if (intake.Status == "voided")
            throw new InvalidOperationException("Cannot update a voided intake.");

        await using var tx = await _db.Database.BeginTransactionAsync(ct);

        // Track chief complaint change
        if (intake.ChiefComplaint != request.ChiefComplaint)
        {
            _db.IntakeAuditLogs.Add(IntakeAuditLog.Create(
                request.IntakeId, "update", "ChiefComplaint",
                intake.ChiefComplaint, request.ChiefComplaint, request.ChangedBy, null));
        }

        // Replace all detail rows (delete + re-insert within transaction)
        var oldHistories = await _db.IntakeMedicalHistories.Where(h => h.IntakeId == request.IntakeId).ToListAsync(ct);
        _db.IntakeMedicalHistories.RemoveRange(oldHistories);

        var oldMeds = await _db.IntakeMedications.Where(m => m.IntakeId == request.IntakeId).ToListAsync(ct);
        _db.IntakeMedications.RemoveRange(oldMeds);

        var oldAllergies = await _db.IntakeAllergies.Where(a => a.IntakeId == request.IntakeId).ToListAsync(ct);
        _db.IntakeAllergies.RemoveRange(oldAllergies);

        var oldInsurance = await _db.IntakeInsurances.Where(i => i.IntakeId == request.IntakeId).ToListAsync(ct);
        _db.IntakeInsurances.RemoveRange(oldInsurance);

        // Re-insert with new values
        foreach (var h in request.MedicalHistory)
            _db.IntakeMedicalHistories.Add(IntakeMedicalHistory.Create(request.IntakeId, h.ConditionName, h.ConditionCode, h.ConfidenceScore, null));

        foreach (var m in request.Medications)
            _db.IntakeMedications.Add(IntakeMedication.Create(request.IntakeId, m.MedicationName, m.Dosage, m.Frequency, m.Route, m.ConfidenceScore, null));

        foreach (var a in request.Allergies)
            _db.IntakeAllergies.Add(IntakeAllergy.Create(request.IntakeId, a.AllergenType, a.AllergenName, a.ReactionType, a.ReactionDescription, a.Severity, a.ConfidenceScore));

        if (request.InsuranceInfo is { } ins)
            _db.IntakeInsurances.Add(IntakeInsurance.Create(request.IntakeId, ins.InsuranceName, ins.MemberId, ins.GroupNumber, ins.PlanName, null, null));

        intake.UpdateChiefComplaintAndTimestamp(request.ChiefComplaint);

        _db.IntakeAuditLogs.Add(IntakeAuditLog.Create(
            request.IntakeId, "update", "AllSections", null, "updated", request.ChangedBy, null));

        await _db.SaveChangesAsync(ct);
        await tx.CommitAsync(ct);

        return await LoadFullAsync(intake, ct);
    }

    public async Task VoidAsync(int intakeId, string reason, string changedBy, CancellationToken ct = default)
    {
        var intake = await _db.IntakeResponses.FindAsync([intakeId], ct)
            ?? throw new InvalidOperationException($"IntakeResponse {intakeId} not found.");

        var previousStatus = intake.Status;
        intake.Void(reason);

        _db.IntakeAuditLogs.Add(IntakeAuditLog.Create(
            intakeId, "void", "Status", previousStatus, "voided", changedBy, reason));

        await _db.SaveChangesAsync(ct);
    }

    private async Task<GetIntakeResult> LoadFullAsync(IntakeResponse intake, CancellationToken ct)
    {
        var histories = await _db.IntakeMedicalHistories.AsNoTracking()
            .Where(h => h.IntakeId == intake.Id).ToListAsync(ct);

        var medications = await _db.IntakeMedications.AsNoTracking()
            .Where(m => m.IntakeId == intake.Id).ToListAsync(ct);

        var allergies = await _db.IntakeAllergies.AsNoTracking()
            .Where(a => a.IntakeId == intake.Id).ToListAsync(ct);

        var insurance = await _db.IntakeInsurances.AsNoTracking()
            .FirstOrDefaultAsync(i => i.IntakeId == intake.Id, ct);

        return new GetIntakeResult(
            intake.Id,
            intake.AppointmentId,
            intake.PatientId,
            intake.Mode,
            intake.Status,
            intake.ChiefComplaint,
            intake.CompletedAt,
            intake.CreatedAt,
            histories.Select(h => new IntakeHistoryItem(h.ConditionName, h.ConditionCode, h.ConfidenceScore)).ToList(),
            medications.Select(m => new IntakeMedicationItem(m.MedicationName, m.Dosage, m.Frequency, m.Route, m.ConfidenceScore)).ToList(),
            allergies.Select(a => new IntakeAllergyItem(a.AllergenType, a.AllergenName, a.ReactionType, a.ReactionDescription, a.Severity, a.ConfidenceScore)).ToList(),
            insurance is null ? null : new IntakeInsuranceItem(insurance.InsuranceName, insurance.MemberId, insurance.GroupNumber, insurance.PlanName)
        );
    }
}
