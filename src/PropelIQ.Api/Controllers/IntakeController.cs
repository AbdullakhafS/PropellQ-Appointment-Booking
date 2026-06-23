using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.DTOs.Common;
using PropelIQ.Api.DTOs.Intake;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api")]
[Produces("application/json")]
public sealed class IntakeController : ControllerBase
{
    private readonly IManualIntakeService _intakeService;
    private readonly IInsurancePreCheckService _insurancePreCheck;
    private readonly IIntakeStorageService _intakeStorage;
    private readonly ILogger<IntakeController> _logger;

    public IntakeController(
        IManualIntakeService intakeService,
        IInsurancePreCheckService insurancePreCheck,
        IIntakeStorageService intakeStorage,
        ILogger<IntakeController> logger)
    {
        _intakeService = intakeService;
        _insurancePreCheck = insurancePreCheck;
        _intakeStorage = intakeStorage;
        _logger = logger;
    }

    /// <summary>
    /// Returns the most recent completed intake record for a patient for auto-population.
    /// </summary>
    /// <response code="200">Previous intake data found and returned.</response>
    /// <response code="204">No prior intake exists for this patient.</response>
    /// <response code="400">Invalid patientId.</response>
    [HttpGet("patients/{patientId:int}/intake/last")]
    [ProducesResponseType(typeof(ApiResponse<LastIntakeResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> GetLastIntake(int patientId, CancellationToken ct)
    {
        if (patientId <= 0)
            return BadRequest(ApiResponse<object>.Fail("Invalid patientId."));

        var result = await _intakeService.GetLastIntakeAsync(patientId, ct);

        if (result is null)
            return NoContent();

        return Ok(ApiResponse<LastIntakeResponseDto>.Ok(MapLastIntake(result)));
    }

    /// <summary>
    /// Submits a completed manual intake form.
    /// </summary>
    /// <response code="200">Intake submitted and persisted.</response>
    /// <response code="400">Validation error in request body.</response>
    [HttpPost("intake/submit")]
    [ProducesResponseType(typeof(ApiResponse<SubmitManualIntakeResponseDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<SubmitManualIntakeResponseDto>), StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> SubmitIntake(
        [FromBody] SubmitManualIntakeRequestDto request,
        CancellationToken ct)
    {
        var serviceRequest = new SubmitManualIntakeRequest(
            request.AppointmentId,
            request.PatientId,
            request.ChiefComplaint,
            request.MedicalHistory ?? [],
            request.OtherConditions,
            (request.Medications ?? [])
                .Select(m => new MedicationEntryDto(m.Name, m.Dosage, m.Frequency))
                .ToList(),
            (request.Allergies ?? [])
                .Select(a => new AllergyEntryDto(a.Allergen, a.Reaction, a.Type ?? "Unknown"))
                .ToList(),
            request.InsuranceInfo is { } ins
                ? new InsuranceInfoDto(ins.Provider, ins.MemberId, ins.GroupNumber, ins.PlanName)
                : null
        );

        var result = await _intakeService.SubmitAsync(serviceRequest, ct);

        // Soft insurance pre-check — never blocks submission
        InsurancePreCheckResponseDto? insuranceResult = null;
        if (request.InsuranceInfo is not null)
        {
            var checkResult = await _insurancePreCheck.CheckAsync(
                new InsurancePreCheckRequest(
                    request.AppointmentId,
                    request.PatientId,
                    request.InsuranceInfo.Provider,
                    request.InsuranceInfo.MemberId,
                    request.InsuranceInfo.GroupNumber),
                ct);

            insuranceResult = new InsurancePreCheckResponseDto(
                checkResult.MatchedPlanId,
                checkResult.MatchedPlanName,
                checkResult.ConfidenceScore,
                checkResult.VerificationStatus,
                checkResult.Reason,
                checkResult.VerificationStatus == "verified");
        }

        // Persist normalized intake to structured storage — best-effort, never blocks submit
        _ = _intakeStorage.StoreAsync(
            IntakeStorageController.MapRequest(
                new StoreIntakeRequestDto(
                    request.AppointmentId, request.PatientId, "manual",
                    request.ChiefComplaint,
                    (request.MedicalHistory ?? []).Select(c => new IntakeHistoryDto(c, null)).ToList(),
                    (request.Medications ?? []).Select(m => new IntakeMedicationDto(m.Name, m.Dosage, m.Frequency, null)).ToList(),
                    (request.Allergies ?? []).Select(a => new IntakeAllergyDto("drug", a.Allergen, a.Type ?? "unknown", a.Reaction, null)).ToList(),
                    request.InsuranceInfo is { } si ? new IntakeInsuranceDto(si.Provider, si.MemberId, si.GroupNumber, si.PlanName) : null,
                    null),
                verificationStatus: insuranceResult?.VerificationStatus,
                insuranceConfidence: insuranceResult?.ConfidenceScore),
            ct)
            .ContinueWith(t => _logger.LogError(t.Exception, "Normalized intake storage failed for appointment {Id}", request.AppointmentId),
                TaskContinuationOptions.OnlyOnFaulted);

        return Ok(ApiResponse<SubmitManualIntakeResponseDto>.Ok(
            new SubmitManualIntakeResponseDto(result.ConversationId, insuranceResult)));
    }

    private static LastIntakeResponseDto MapLastIntake(LastIntakeResult r)
        => new(
            r.ChiefComplaint,
            r.MedicalHistory,
            r.OtherConditions,
            r.Medications.Select(m => new MedicationFormDto(m.Name ?? string.Empty, m.Dosage, m.Frequency)).ToList(),
            r.Allergies.Select(a => new AllergyFormDto(a.Allergen ?? string.Empty, a.Reaction, a.Type)).ToList(),
            r.InsuranceInfo is { } ins
                ? new InsuranceFormDto(ins.Provider, ins.MemberId, ins.GroupNumber, ins.PlanName)
                : null,
            r.LastUpdatedAt
        );
}
