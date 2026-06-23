using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.DTOs.Common;
using PropelIQ.Api.DTOs.Intake;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/patients/{patientId:int}/intake")]
[Produces("application/json")]
public sealed class PatientIntakeController : ControllerBase
{
    private readonly IIntakeStorageService _storage;
    private readonly ILogger<PatientIntakeController> _logger;

    public PatientIntakeController(IIntakeStorageService storage, ILogger<PatientIntakeController> logger)
    {
        _storage = storage;
        _logger = logger;
    }

    /// <summary>
    /// Returns the most recent completed intake for a patient (profile view).
    /// </summary>
    /// <response code="200">Latest intake found.</response>
    /// <response code="204">No completed intake exists for this patient.</response>
    [HttpGet("latest")]
    [ProducesResponseType(typeof(ApiResponse<ProfileIntakeResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> GetLatest(int patientId, CancellationToken ct)
    {
        var result = await _storage.GetLatestByPatientAsync(patientId, ct);
        if (result is null) return NoContent();

        return Ok(ApiResponse<ProfileIntakeResponseDto>.Ok(MapProfile(result)));
    }

    /// <summary>
    /// Updates an existing intake from the profile edit form.
    /// Locked when appointment is checked in.
    /// </summary>
    /// <response code="200">Intake updated.</response>
    /// <response code="400">Validation error.</response>
    /// <response code="404">Intake not found or voided.</response>
    [HttpPatch("{intakeId:int}")]
    [ProducesResponseType(typeof(ApiResponse<ProfileIntakeResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> UpdateIntake(
        int patientId,
        int intakeId,
        [FromBody] UpdateIntakeRequestDto request,
        CancellationToken ct)
    {
        try
        {
            var updateRequest = new UpdateIntakeRequest(
                intakeId,
                patientId,
                request.ChiefComplaint,
                (request.MedicalHistory ?? []).Select(h => new IntakeHistoryItem(h.ConditionName, h.ConditionCode, h.ConfidenceScore)).ToList(),
                (request.Medications ?? []).Select(m => new IntakeMedicationItem(m.MedicationName, m.Dosage, m.Frequency, m.Route, m.ConfidenceScore)).ToList(),
                (request.Allergies ?? []).Select(a => new IntakeAllergyItem(a.AllergenType, a.AllergenName, a.ReactionType, a.ReactionDescription, a.Severity, a.ConfidenceScore)).ToList(),
                request.InsuranceInfo is { } ins ? new IntakeInsuranceItem(ins.InsuranceName, ins.MemberId, ins.GroupNumber, ins.PlanName) : null,
                $"patient:{patientId}"
            );

            var result = await _storage.UpdateAsync(updateRequest, ct);
            return Ok(ApiResponse<ProfileIntakeResponseDto>.Ok(MapProfile(result)));
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogWarning(ex, "Intake {IntakeId} not found or cannot be updated for patient {PatientId}", intakeId, patientId);
            return NotFound(ApiResponse<object>.Fail(ex.Message));
        }
    }

    private static ProfileIntakeResponseDto MapProfile(GetIntakeResult r)
        => new(
            r.IntakeId,
            r.AppointmentId,
            r.PatientId,
            r.Mode,
            r.Status,
            r.ChiefComplaint,
            r.CompletedAt,
            r.CreatedAt,  // UpdatedAt not in GetIntakeResult; CreatedAt used as proxy
            r.MedicalHistory.Select(h => new ProfileHistoryDto(h.ConditionName, h.ConditionCode, "active", h.ConfidenceScore)).ToList(),
            r.Medications.Select(m => new ProfileMedicationDto(m.MedicationName, m.Dosage, m.Frequency, m.Route, m.ConfidenceScore)).ToList(),
            r.Allergies.Select(a => new ProfileAllergyDto(a.AllergenType, a.AllergenName, a.ReactionType, a.ReactionDescription, a.Severity, a.ConfidenceScore)).ToList(),
            r.InsuranceInfo is { } ins
                ? new ProfileInsuranceDto(ins.InsuranceName, ins.MemberId, ins.GroupNumber, ins.PlanName, null, null)
                : null
        );
}
