using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.DTOs.Common;
using PropelIQ.Api.DTOs.Intake;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/intake/structured")]
[Produces("application/json")]
public sealed class IntakeStorageController : ControllerBase
{
    private readonly IIntakeStorageService _storage;
    private readonly ILogger<IntakeStorageController> _logger;

    public IntakeStorageController(IIntakeStorageService storage, ILogger<IntakeStorageController> logger)
    {
        _storage = storage;
        _logger = logger;
    }

    /// <summary>
    /// Stores a completed intake payload across all normalized tables in a single transaction.
    /// </summary>
    /// <response code="200">Intake stored; returns intake_id and completed_at.</response>
    /// <response code="400">Validation error in request body.</response>
    [HttpPost]
    [ProducesResponseType(typeof(ApiResponse<StoreIntakeResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<StoreIntakeResponseDto>), StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Store(
        [FromBody] StoreIntakeRequestDto request,
        CancellationToken ct)
    {
        var serviceRequest = MapRequest(request, verificationStatus: null, insuranceConfidence: null);
        var result = await _storage.StoreAsync(serviceRequest, ct);

        return Ok(ApiResponse<StoreIntakeResponseDto>.Ok(
            new StoreIntakeResponseDto(result.IntakeId, result.AppointmentId, result.CompletedAt)));
    }

    /// <summary>
    /// Returns the latest completed intake record for an appointment.
    /// </summary>
    /// <response code="200">Intake record found.</response>
    /// <response code="204">No intake record exists for this appointment.</response>
    [HttpGet("appointment/{appointmentId:int}")]
    [ProducesResponseType(typeof(ApiResponse<GetIntakeResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> GetByAppointment(int appointmentId, CancellationToken ct)
    {
        var result = await _storage.GetByAppointmentAsync(appointmentId, ct);
        if (result is null) return NoContent();

        return Ok(ApiResponse<GetIntakeResponseDto>.Ok(MapResult(result)));
    }

    /// <summary>
    /// Returns all completed intake records for a patient.
    /// </summary>
    /// <response code="200">List of intake records (may be empty).</response>
    [HttpGet("patient/{patientId:int}")]
    [ProducesResponseType(typeof(ApiResponse<IReadOnlyList<GetIntakeResponseDto>>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetByPatient(int patientId, CancellationToken ct)
    {
        var results = await _storage.GetByPatientAsync(patientId, ct);
        return Ok(ApiResponse<IReadOnlyList<GetIntakeResponseDto>>.Ok(
            results.Select(MapResult).ToList()));
    }

    /// <summary>
    /// Voids (soft-deletes) an intake record.
    /// </summary>
    /// <response code="204">Intake voided.</response>
    /// <response code="404">Intake not found.</response>
    [HttpDelete("{intakeId:int}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Void(int intakeId, [FromQuery] string? reason, CancellationToken ct)
    {
        try
        {
            await _storage.VoidAsync(intakeId, reason ?? "Voided via API", "api", ct);
            return NoContent();
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogWarning(ex, "IntakeResponse {Id} not found for void", intakeId);
            return NotFound();
        }
    }

    internal static StoreIntakeRequest MapRequest(
        StoreIntakeRequestDto r,
        string? verificationStatus,
        int? insuranceConfidence)
        => new(
            r.AppointmentId,
            r.PatientId,
            r.Mode,
            r.ChiefComplaint,
            (r.MedicalHistory ?? []).Select(h => new IntakeHistoryItem(h.ConditionName, h.ConditionCode, h.ConfidenceScore)).ToList(),
            (r.Medications ?? []).Select(m => new IntakeMedicationItem(m.MedicationName, m.Dosage, m.Frequency, m.Route, m.ConfidenceScore)).ToList(),
            (r.Allergies ?? []).Select(a => new IntakeAllergyItem(a.AllergenType, a.AllergenName, a.ReactionType, a.ReactionDescription, a.Severity, a.ConfidenceScore)).ToList(),
            r.InsuranceInfo is { } ins ? new IntakeInsuranceItem(ins.InsuranceName, ins.MemberId, ins.GroupNumber, ins.PlanName) : null,
            verificationStatus,
            insuranceConfidence,
            r.Notes,
            null
        );

    private static GetIntakeResponseDto MapResult(GetIntakeResult r)
        => new(
            r.IntakeId, r.AppointmentId, r.PatientId, r.Mode, r.Status, r.ChiefComplaint, r.CompletedAt, r.CreatedAt,
            r.MedicalHistory.Select(h => new IntakeHistoryDto(h.ConditionName, h.ConditionCode, h.ConfidenceScore)).ToList(),
            r.Medications.Select(m => new IntakeMedicationDto(m.MedicationName, m.Dosage, m.Frequency, m.Route, m.ConfidenceScore)).ToList(),
            r.Allergies.Select(a => new IntakeAllergyDto(a.AllergenType, a.AllergenName, a.ReactionType, a.ReactionDescription, a.Severity, a.ConfidenceScore)).ToList(),
            r.InsuranceInfo is { } ins ? new IntakeInsuranceDto(ins.InsuranceName, ins.MemberId, ins.GroupNumber, ins.PlanName) : null
        );
}
