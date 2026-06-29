using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Serialization;
using System.Globalization;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.DTOs.Appointments;
using PropelIQ.Api.Services;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

[ApiController]
[Route("api/appointments")]
[Produces("application/json")]
public sealed class AppointmentController : ControllerBase
{
    private static readonly string[] SupportedDateFormats =
    {
        "yyyy-MM-dd",
        "dd-MM-yyyy",
        "dd/MM/yyyy",
        "MM-dd-yyyy",
        "MM/dd/yyyy",
    };

    private readonly IAppointmentDetailService _detail;
    private readonly ISlotAvailabilityService _slots;
    private readonly LegacyBookingStore _bookingStore;
    private readonly IWalkInBookingService _walkInBooking;
    private readonly ILogger<AppointmentController> _logger;

    public AppointmentController(
        IAppointmentDetailService detail,
        ISlotAvailabilityService slots,
        LegacyBookingStore bookingStore,
        IWalkInBookingService walkInBooking,
        ILogger<AppointmentController> logger)
    {
        _detail = detail;
        _slots = slots;
        _bookingStore = bookingStore;
        _walkInBooking = walkInBooking;
        _logger = logger;
    }

    /// <summary>
    /// Legacy-compatible slot search endpoint used by the current frontend.
    /// </summary>
    [AllowAnonymous]
    [HttpGet("search")]
    public async Task<IActionResult> Search(
        [FromQuery] string? dateFrom,
        [FromQuery] string? dateTo,
        [FromQuery] string? timeOfDay,
        [FromQuery] string? provider,
        [FromQuery] string? specialty,
        [FromQuery] string? sortBy = "date",
        [FromQuery] string? sortDir = "asc",
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 10,
        CancellationToken ct = default)
    {
        var startedAt = DateTime.UtcNow;
        var window = BuildWindow(dateFrom, dateTo);
        var slots = await _slots.GetAvailableSlotsAsync(
            new SlotAvailabilityQuery(null, null, window.Start, window.End), ct);

        IEnumerable<AvailableSlot> filtered = slots.Where(s => !_bookingStore.IsBooked(ToLegacyId(s)));

        if (!string.IsNullOrWhiteSpace(provider))
        {
            filtered = filtered.Where(s =>
                s.ProviderName.Contains(provider, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(timeOfDay))
        {
            filtered = filtered.Where(s => MatchesTimeOfDay(s.StartTime, timeOfDay));
        }

        // The current slot seed does not carry specialty metadata, so we expose a default value.
        if (!string.IsNullOrWhiteSpace(specialty) &&
            !specialty.Equals("General Practice", StringComparison.OrdinalIgnoreCase))
        {
            filtered = Enumerable.Empty<AvailableSlot>();
        }

        filtered = (sortBy ?? "date").Equals("provider", StringComparison.OrdinalIgnoreCase)
            ? (sortDir ?? "asc").Equals("desc", StringComparison.OrdinalIgnoreCase)
                ? filtered.OrderByDescending(s => s.ProviderName).ThenByDescending(s => s.StartTime)
                : filtered.OrderBy(s => s.ProviderName).ThenBy(s => s.StartTime)
            : (sortDir ?? "asc").Equals("desc", StringComparison.OrdinalIgnoreCase)
                ? filtered.OrderByDescending(s => s.StartTime)
                : filtered.OrderBy(s => s.StartTime);

        var safePageSize = Math.Clamp(pageSize, 1, 100);
        var safePage = Math.Max(page, 1);
        var total = filtered.Count();
        var totalPages = Math.Max(1, (int)Math.Ceiling(total / (double)safePageSize));
        var pageItems = filtered
            .Skip((safePage - 1) * safePageSize)
            .Take(safePageSize)
            .Select(ToSearchItem)
            .ToList();

        var latencyMs = (DateTime.UtcNow - startedAt).TotalMilliseconds;
        return Ok(new
        {
            success = true,
            data = new
            {
                items = pageItems,
                pagination = new
                {
                    page = safePage,
                    pageSize = safePageSize,
                    total,
                    totalPages,
                }
            },
            meta = new
            {
                latencyMs = Math.Round(latencyMs, 2),
            }
        });
    }

    /// <summary>
    /// Legacy-compatible specialties endpoint used by the current frontend.
    /// </summary>
    [AllowAnonymous]
    [HttpGet("specialties")]
    public IActionResult Specialties()
    {
        return Ok(new
        {
            success = true,
            data = new[]
            {
                new { name = "General Practice" }
            }
        });
    }

    /// <summary>
    /// Legacy-compatible calendar endpoint used by the current frontend.
    /// </summary>
    [AllowAnonymous]
    [HttpGet("calendar")]
    public async Task<IActionResult> Calendar(
        [FromQuery] string? dateFrom,
        [FromQuery] string? dateTo,
        [FromQuery] string? view,
        [FromQuery] string? anchorDate,
        CancellationToken ct = default)
    {
        var window = BuildWindow(dateFrom, dateTo, view, anchorDate);
        var todayStart = new DateTimeOffset(DateTime.UtcNow.Date, TimeSpan.Zero);
        var effectiveStart = window.Start < todayStart ? todayStart : window.Start;

        if (window.End < effectiveStart)
        {
            window = (effectiveStart, effectiveStart.AddDays(27), DateOnly.FromDateTime(effectiveStart.UtcDateTime));
        }

        var slots = await _slots.GetAvailableSlotsAsync(
            new SlotAvailabilityQuery(null, null, effectiveStart, window.End), ct);

        var days = new List<object>();
        for (var d = effectiveStart.Date; d <= window.End.Date; d = d.AddDays(1))
        {
            var daySlots = slots
                .Where(s => s.StartTime.Date == d)
                .OrderBy(s => s.StartTime)
                .Select(s => new
                {
                    id = ToLegacyId(s),
                    status = _bookingStore.IsBooked(ToLegacyId(s)) ? "booked" : "available",
                    provider_name = s.ProviderName,
                    appointment_date = s.StartTime.ToString("yyyy-MM-dd"),
                    start_time = s.StartTime.ToString("HH:mm"),
                })
                .Cast<object>()
                .ToList();

            days.Add(new
            {
                dayLabel = d.ToString("ddd"),
                dayNumber = d.Day,
                isCurrentMonth = d.Month == window.AnchorDate.Month,
                slots = daySlots,
            });
        }

        return Ok(new
        {
            success = true,
            data = new
            {
                anchorDate = window.AnchorDate.ToString("yyyy-MM-dd"),
                rangeStart = effectiveStart.ToString("yyyy-MM-dd"),
                rangeEnd = window.End.ToString("yyyy-MM-dd"),
                timezone = "UTC",
                utcFooter = "Times shown in UTC.",
                days,
            }
        });
    }

    /// <summary>
    /// Legacy-compatible appointment detail by numeric slot id.
    /// </summary>
    [AllowAnonymous]
    [HttpGet("{appointmentId:int}")]
    public async Task<IActionResult> GetLegacyDetail(int appointmentId, CancellationToken ct = default)
    {
        var slot = await FindSlotByLegacyIdAsync(appointmentId, ct);
        if (slot is null)
        {
            return NotFound(new
            {
                success = false,
                error = new { code = "APPOINTMENT_NOT_FOUND", message = "Appointment not found" }
            });
        }

        return Ok(new
        {
            success = true,
            data = ToLegacyDetail(slot)
        });
    }

    /// <summary>
    /// Legacy-compatible reserve endpoint.
    /// </summary>
    [AllowAnonymous]
    [HttpPost("{appointmentId:int}/checkout")]
    public async Task<IActionResult> Checkout(int appointmentId, CancellationToken ct = default)
    {
        var slot = await FindSlotByLegacyIdAsync(appointmentId, ct);
        if (slot is null)
        {
            return Conflict(new
            {
                success = false,
                error = new { code = "UNAVAILABLE_SLOT", message = "Selected appointment slot is no longer available" }
            });
        }

        if (_bookingStore.IsBooked(appointmentId))
        {
            return Conflict(new
            {
                success = false,
                error = new { code = "UNAVAILABLE_SLOT", message = "Selected appointment slot is no longer available" }
            });
        }

        var now = DateTimeOffset.UtcNow;
        if (_bookingStore.HasActiveReservation(appointmentId, now))
        {
            return Conflict(new
            {
                success = false,
                error = new { code = "RESERVED", message = "Selected appointment slot is currently reserved" }
            });
        }

        var reservation = _bookingStore.CreateReservation(appointmentId, now);

        return Ok(new
        {
            success = true,
            data = new
            {
                reservationToken = reservation.Token,
                expiresAt = reservation.ExpiresAt,
            }
        });
    }

    /// <summary>
    /// Legacy-compatible finalize booking endpoint.
    /// </summary>
    [AllowAnonymous]
    [HttpPost("book")]
    public async Task<IActionResult> Book([FromBody] LegacyBookRequest? req, CancellationToken ct = default)
    {
        var reservationToken = req?.GetReservationToken();
        if (string.IsNullOrWhiteSpace(reservationToken))
        {
            // Staff walk-in flow can create a booking directly without a reservation token.
            if (req?.IsWalkInRequest() == true)
            {
                var appointmentDate = TryParseDateOnlyFlexible(req.Date, out var parsedDate)
                    ? parsedDate
                    : DateOnly.FromDateTime(DateTime.UtcNow);

                var patient = await _walkInBooking.CreatePatientAsync(new CreatePatientRequest(
                    req.FirstName!.Trim(),
                    req.LastName!.Trim(),
                    // Legacy walk-in form does not collect DOB, so we use a safe placeholder.
                    DateOnly.FromDateTime(DateTime.UtcNow.AddYears(-30)),
                    req.Phone!.Trim(),
                    "unknown",
                    req.Email?.Trim(),
                    null,
                    "Created via legacy staff walk-in flow"), ct);

                var appointmentTime = new DateTimeOffset(
                    appointmentDate.Year,
                    appointmentDate.Month,
                    appointmentDate.Day,
                    DateTime.UtcNow.Hour,
                    0,
                    0,
                    TimeSpan.Zero);

                var booked = await _walkInBooking.BookWalkInAsync(new BookWalkInRequest(
                    patient.Id,
                    req.GetProviderName(),
                    appointmentTime,
                    30,
                    "Booked via legacy /api/appointments/book"), ct);

                var walkInId = Math.Abs(BitConverter.ToInt32(SHA256.HashData(booked.AppointmentId.ToByteArray()), 0));
                return Ok(new
                {
                    success = true,
                    data = new
                    {
                        id = walkInId,
                        appointmentId = walkInId,
                        status = "booked",
                        message = "Walk-in appointment created successfully"
                    }
                });
            }

            return BadRequest(new
            {
                success = false,
                error = new { code = "RESERVATION_EXPIRED", message = "Reservation token is required" }
            });
        }

        var consumed = _bookingStore.ConsumeReservation(reservationToken, DateTimeOffset.UtcNow);
        if (!consumed.Success)
        {
            return Conflict(new
            {
                success = false,
                error = new { code = "RESERVATION_EXPIRED", message = "Reservation expired or invalid" }
            });
        }

        AvailableSlot? bookedSlot = null;
        if (req?.AppointmentId is int appointmentId)
        {
            bookedSlot = await FindSlotByLegacyIdAsync(appointmentId, ct);
        }

        return Ok(new
        {
            success = true,
            data = new
            {
                id = consumed.AppointmentId,
                appointmentId = consumed.AppointmentId,
                provider_name = bookedSlot?.ProviderName,
                appointment_date = bookedSlot?.StartTime.ToString("yyyy-MM-dd"),
                start_time = bookedSlot?.StartTime.ToString("HH:mm"),
                end_time = bookedSlot?.EndTime.ToString("HH:mm"),
                location = bookedSlot?.Location,
                status = "booked",
                message = "Appointment booked successfully",
            }
        });
    }

    /// <summary>
    /// Legacy-compatible provider suggestions endpoint.
    /// </summary>
    [AllowAnonymous]
    [HttpGet("/api/providers/suggest")]
    public async Task<IActionResult> SuggestProviders([FromQuery] string? query, CancellationToken ct = default)
    {
        var q = (query ?? string.Empty).Trim();
        if (q.Length < 2)
        {
            return Ok(new { success = true, data = Array.Empty<object>() });
        }

        var slots = await QuerySlotsAsync(ct);
        var providers = slots
            .GroupBy(s => s.ProviderId)
            .Select(g => new
            {
                providerId = ToProviderLegacyId(g.Key),
                name = g.First().ProviderName,
                specialty = "General Practice",
            })
            .Where(p => p.name.Contains(q, StringComparison.OrdinalIgnoreCase))
            .OrderBy(p => p.name)
            .Take(10)
            .Cast<object>()
            .ToList();

        return Ok(new { success = true, data = providers });
    }

    /// <summary>
    /// Legacy-compatible provider details endpoint.
    /// </summary>
    [AllowAnonymous]
    [HttpGet("/api/providers/{providerId:int}")]
    public async Task<IActionResult> GetProvider(int providerId, CancellationToken ct = default)
    {
        var slots = await QuerySlotsAsync(ct);
        var provider = slots
            .GroupBy(s => s.ProviderId)
            .Select(g => new
            {
                id = ToProviderLegacyId(g.Key),
                name = g.First().ProviderName,
            })
            .FirstOrDefault(p => p.id == providerId);

        if (provider is null)
        {
            return NotFound(new
            {
                success = false,
                error = new { code = "PROVIDER_NOT_FOUND", message = "Provider not found" }
            });
        }

        return Ok(new
        {
            success = true,
            data = new
            {
                id = provider.id,
                name = provider.name,
                specialty = "General Practice",
                credentials = "MD",
                bio = "Experienced clinician focused on patient-centered care.",
                review_count = 0,
                photo_url = ""
            }
        });
    }

    /// <summary>
    /// Returns full appointment detail including arrival timestamp and complete status history.
    /// </summary>
    /// <response code="200">Appointment detail with arrival metadata.</response>
    /// <response code="404">Appointment not found.</response>
    [HttpGet("{appointmentId:guid}")]
    [ProducesResponseType(typeof(ApiResponse<AppointmentDetailDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public IActionResult GetDetail(Guid appointmentId)
    {
        var detail = _detail.GetDetail(appointmentId);
        if (detail is null)
        {
            _logger.LogWarning("Appointment {Id} not found for detail lookup", appointmentId);
            return NotFound(ApiResponse<object>.Fail($"Appointment {appointmentId} not found."));
        }

        return Ok(ApiResponse<AppointmentDetailDto>.Ok(new AppointmentDetailDto(
            detail.AppointmentId,
            detail.PatientId,
            detail.PatientFullName,
            detail.ProviderName,
            detail.AppointmentTime,
            detail.DurationMinutes,
            detail.IsWalkIn,
            detail.Status,
            detail.CreatedAt,
            detail.ArrivedAt,
            detail.StatusHistory.Select(h => new AppointmentHistoryEntryDto(
                h.Id, h.PreviousStatus, h.NewStatus, h.TransitionedAtUtc, h.Notes)).ToList())));
    }

    /// <summary>
    /// Returns the status-transition history for an appointment.
    /// Supports SLA tracking, arrival-order analysis, and patient flow metrics.
    /// </summary>
    /// <response code="200">Ordered list of status transitions (oldest first).</response>
    [HttpGet("{appointmentId:guid}/history")]
    [ProducesResponseType(typeof(ApiResponse<IReadOnlyList<AppointmentHistoryEntryDto>>), StatusCodes.Status200OK)]
    public IActionResult GetHistory(Guid appointmentId)
    {
        var history = _detail.GetHistory(appointmentId);
        return Ok(ApiResponse<IReadOnlyList<AppointmentHistoryEntryDto>>.Ok(
            history.Select(h => new AppointmentHistoryEntryDto(
                h.Id, h.PreviousStatus, h.NewStatus, h.TransitionedAtUtc, h.Notes)).ToList()));
    }

    private static (DateTimeOffset Start, DateTimeOffset End, DateOnly AnchorDate) BuildWindow(
        string? dateFrom,
        string? dateTo,
        string? view = null,
        string? anchorDate = null)
    {
        var utcToday = DateOnly.FromDateTime(DateTime.UtcNow);
        var start = TryParseDateOnlyFlexible(dateFrom, out var parsedFrom) ? parsedFrom : utcToday;

        DateOnly end;
        if (TryParseDateOnlyFlexible(dateTo, out var parsedTo))
        {
            end = parsedTo;
        }
        else
        {
            var spanDays = (view ?? "month").Equals("week", StringComparison.OrdinalIgnoreCase) ? 13 : 27;
            end = start.AddDays(spanDays);
        }

        if (TryParseDateOnlyFlexible(anchorDate, out var parsedAnchor))
        {
            start = parsedAnchor;
            if (!TryParseDateOnlyFlexible(dateTo, out _))
            {
                var spanDays = (view ?? "month").Equals("week", StringComparison.OrdinalIgnoreCase) ? 13 : 27;
                end = parsedAnchor.AddDays(spanDays);
            }
        }

        if (end < start)
        {
            (start, end) = (end, start);
        }

        var startUtc = new DateTimeOffset(start.ToDateTime(TimeOnly.MinValue), TimeSpan.Zero);
        var endUtc = new DateTimeOffset(end.ToDateTime(new TimeOnly(23, 59, 59)), TimeSpan.Zero);
        return (startUtc, endUtc, start);
    }

    private static bool TryParseDateOnlyFlexible(string? value, out DateOnly parsed)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            parsed = default;
            return false;
        }

        var candidate = value.Trim();
        return DateOnly.TryParseExact(candidate, SupportedDateFormats, CultureInfo.InvariantCulture, DateTimeStyles.None, out parsed)
            || DateOnly.TryParse(candidate, CultureInfo.InvariantCulture, DateTimeStyles.None, out parsed)
            || DateOnly.TryParse(candidate, CultureInfo.CurrentCulture, DateTimeStyles.None, out parsed);
    }

    private static bool MatchesTimeOfDay(DateTimeOffset startTime, string? timeOfDay)
    {
        if (string.IsNullOrWhiteSpace(timeOfDay))
        {
            return true;
        }

        return timeOfDay.Trim().ToLowerInvariant() switch
        {
            "morning" => startTime.Hour < 12,
            "afternoon" => startTime.Hour >= 12 && startTime.Hour < 17,
            "evening" => startTime.Hour >= 17,
            _ => true,
        };
    }

    private static int ToLegacyId(AvailableSlot slot)
    {
        var key = $"{slot.ProviderId}|{slot.StartTime.UtcDateTime:O}|{slot.EndTime.UtcDateTime:O}";
        using var sha = SHA256.Create();
        var bytes = sha.ComputeHash(Encoding.UTF8.GetBytes(key));
        return Math.Abs(BitConverter.ToInt32(bytes, 0));
    }

    private static object ToSearchItem(AvailableSlot slot)
    {
        return new
        {
            id = ToLegacyId(slot),
            provider_id = ToProviderLegacyId(slot.ProviderId),
            provider_name = slot.ProviderName,
            specialty = "General Practice",
            appointment_date = slot.StartTime.ToString("yyyy-MM-dd"),
            start_time = slot.StartTime.ToString("HH:mm"),
            end_time = slot.EndTime.ToString("HH:mm"),
            location = slot.Location,
            duration_minutes = slot.DurationMinutes,
            status = "available",
        };
    }

    private static int ToProviderLegacyId(string providerId)
    {
        var digits = new string(providerId.Where(char.IsDigit).ToArray());
        return int.TryParse(digits, out var parsed) ? parsed : Math.Abs(providerId.GetHashCode());
    }

    private async Task<AvailableSlot?> FindSlotByLegacyIdAsync(int appointmentId, CancellationToken ct)
    {
        var slots = await QuerySlotsAsync(ct);
        return slots.FirstOrDefault(s => ToLegacyId(s) == appointmentId);
    }

    private async Task<IReadOnlyList<AvailableSlot>> QuerySlotsAsync(CancellationToken ct)
    {
        var start = DateTimeOffset.UtcNow.AddDays(-1);
        var end = DateTimeOffset.UtcNow.AddDays(31);
        return await _slots.GetAvailableSlotsAsync(new SlotAvailabilityQuery(null, null, start, end), ct);
    }

    private object ToLegacyDetail(AvailableSlot slot)
    {
        var now = DateTimeOffset.UtcNow;
        var appointmentId = ToLegacyId(slot);
        var isBooked = _bookingStore.IsBooked(appointmentId);
        var hasReservation = !isBooked && _bookingStore.HasActiveReservation(appointmentId, now);

        return new
        {
            id = appointmentId,
            provider_id = ToProviderLegacyId(slot.ProviderId),
            provider_name = slot.ProviderName,
            specialty = "General Practice",
            credentials = "MD",
            appointment_date = slot.StartTime.ToString("yyyy-MM-dd"),
            start_time = slot.StartTime.ToString("HH:mm"),
            end_time = slot.EndTime.ToString("HH:mm"),
            location = slot.Location,
            duration_minutes = slot.DurationMinutes,
            status = isBooked ? "booked" : "available",
            checkout_status = hasReservation ? "reserved" : "searching",
            bio = "Experienced clinician focused on patient-centered care.",
            photo_url = "",
        };
    }
}

public sealed class LegacyBookRequest
{
    [JsonPropertyName("reservationToken")]
    public string? ReservationToken { get; init; }

    [JsonPropertyName("reservation_token")]
    public string? ReservationTokenSnakeCase { get; init; }

    [JsonPropertyName("token")]
    public string? Token { get; init; }

    public string? FirstName { get; init; }
    public string? LastName { get; init; }
    public string? Email { get; init; }
    public string? Phone { get; init; }

    [JsonPropertyName("appointmentId")]
    public int? AppointmentId { get; init; }

    public string? Date { get; init; }

    [JsonPropertyName("providerName")]
    public string? ProviderName { get; init; }

    [JsonPropertyName("provider_name")]
    public string? ProviderNameSnakeCase { get; init; }

    [JsonPropertyName("specialtyId")]
    public string? SpecialtyId { get; init; }

    public string? GetReservationToken()
    {
        return ReservationToken
            ?? ReservationTokenSnakeCase
            ?? Token;
    }

    public bool IsWalkInRequest()
    {
        return !string.IsNullOrWhiteSpace(FirstName)
            && !string.IsNullOrWhiteSpace(LastName)
            && !string.IsNullOrWhiteSpace(Email)
            && !string.IsNullOrWhiteSpace(Phone)
            && (!string.IsNullOrWhiteSpace(Date) || AppointmentId.HasValue);
    }

    public string GetProviderName()
    {
        if (!string.IsNullOrWhiteSpace(ProviderName))
        {
            return ProviderName.Trim();
        }

        if (!string.IsNullOrWhiteSpace(ProviderNameSnakeCase))
        {
            return ProviderNameSnakeCase.Trim();
        }

        if (!string.IsNullOrWhiteSpace(SpecialtyId))
        {
            return $"Walk-in ({SpecialtyId.Trim()})";
        }

        return "Walk-in Provider";
    }
}
