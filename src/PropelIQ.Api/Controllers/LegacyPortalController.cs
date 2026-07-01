using System.Collections.Concurrent;
using System.Text;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using PropelIQ.Api.Services;
using PropelIQ.Application.Interfaces.Services;
using PropelIQ.Application.Models;

namespace PropelIQ.Api.Controllers;

[ApiController]
[AllowAnonymous]
public sealed class LegacyPortalController : ControllerBase
{
    private readonly SessionStore _sessions;
    private readonly IQueueService _queue;
    private readonly IWalkInBookingService _walkIn;

    private static readonly ConcurrentDictionary<string, IntegrationState> Integrations = new(StringComparer.OrdinalIgnoreCase)
    {
        ["google"] = new IntegrationState(false, "revoked"),
        ["outlook"] = new IntegrationState(false, "revoked")
    };

    private static readonly ConcurrentDictionary<string, NotificationPreferences> NotificationPrefsByPatient = new(StringComparer.OrdinalIgnoreCase)
    {
    };

    private static readonly ConcurrentDictionary<string, decimal> Thresholds = new(StringComparer.OrdinalIgnoreCase)
    {
        ["icd10"] = 0.70m,
        ["cpt"] = 0.75m
    };

    private static readonly List<ThresholdHistoryItem> ThresholdHistory = new();
    private static readonly object ThresholdLock = new();
    private static readonly List<PatientDocumentItem> PatientDocuments = [];
    private static readonly object PatientDocumentsLock = new();
    private static readonly List<object> AdminAuditEvents =
    [
        new
        {
            timestamp = DateTimeOffset.UtcNow.AddMinutes(-35),
            eventType = "login_success",
            actorId = "admin1",
            message = "Admin session issued",
            details = new { endpoint = "/api/auth/session", ip = "127.0.0.1" }
        },
        new
        {
            timestamp = DateTimeOffset.UtcNow.AddMinutes(-20),
            eventType = "account_update",
            actorId = "admin1",
            message = "Updated user role",
            details = new { targetUser = "staff1", oldRole = "staff", newRole = "staff" }
        },
        new
        {
            timestamp = DateTimeOffset.UtcNow.AddMinutes(-9),
            eventType = "appointment_action",
            actorId = "staff1",
            message = "Checked in appointment",
            details = new { endpoint = "/api/staff/appointments/101/checkin", outcome = "success" }
        }
    ];

    private static readonly List<object> RbacAuditEvents =
    [
        new
        {
            timestamp = DateTimeOffset.UtcNow.AddMinutes(-18),
            role = "admin",
            action = "admin:dashboard",
            endpoint = "/api/admin/operational-metrics",
            outcome = "allowed"
        },
        new
        {
            timestamp = DateTimeOffset.UtcNow.AddMinutes(-12),
            role = "staff",
            action = "staff:queue_view",
            endpoint = "/api/staff/queue",
            outcome = "allowed"
        },
        new
        {
            timestamp = DateTimeOffset.UtcNow.AddMinutes(-6),
            role = "patient",
            action = "admin:dashboard",
            endpoint = "/api/admin/operational-metrics",
            outcome = "denied"
        }
    ];

    public LegacyPortalController(
        SessionStore sessions,
        IQueueService queue,
        IWalkInBookingService walkIn)
    {
        _sessions = sessions;
        _queue = queue;
        _walkIn = walkIn;
    }

    [HttpGet("/api/patient/profile")]
    public IActionResult GetPatientProfile()
    {
        return Ok(new
        {
            success = true,
            data = new
            {
                first_name = "Alex",
                last_name = "Johnson",
                email = "alex.johnson@example.com",
                phone = "+1-555-0100",
                preferred_timezone = "UTC",
                reminder_channels = "[\"email\"]"
            }
        });
    }

    [HttpGet("/api/integrations/status")]
    public IActionResult GetIntegrationsStatus()
    {
        return Ok(new
        {
            success = true,
            data = new
            {
                google = Integrations["google"],
                outlook = Integrations["outlook"]
            }
        });
    }

    [HttpGet("/api/metrics/search")]
    public IActionResult GetSearchMetrics()
    {
        return Ok(new
        {
            success = true,
            data = new
            {
                p95LatencyMs = 82,
                emptyResultRate = 4,
                alertBreached = false
            }
        });
    }

    [HttpGet("/api/dashboard/metrics")]
    public IActionResult GetDashboardMetrics()
    {
        return Ok(new
        {
            success = true,
            data = new
            {
                jobs = new { confirmations = 1, reminders = 1, swaps = 0, calendarSync = 1 },
                bookings = new { booked = 3, conflicts = 0 },
                integrations = new
                {
                    connected = Integrations.Values.Count(v => v.Connected),
                    disconnected = Integrations.Values.Count(v => !v.Connected)
                }
            }
        });
    }

    [HttpPost("/api/jobs/process-confirmations")]
    [HttpPost("/api/jobs/process-reminders")]
    [HttpPost("/api/jobs/process-swaps")]
    [HttpPost("/api/jobs/process-calendar-sync")]
    public IActionResult ProcessJob()
    {
        return Ok(new
        {
            success = true,
            data = new { processedAt = DateTimeOffset.UtcNow }
        });
    }

    [HttpGet("/api/staff/queue")]
    public async Task<IActionResult> GetStaffQueue([FromQuery] string? date, CancellationToken ct = default)
    {
        DateOnly? targetDate = null;
        if (DateTime.TryParse(date, out var parsedDateTime))
        {
            targetDate = DateOnly.FromDateTime(parsedDateTime);
        }

        var queueResult = await _queue.GetQueueAsync(new QueueQuery(
            Date: targetDate,
            Status: null,
            IsWalkIn: null,
            ProviderId: null,
            Page: 1,
            PageSize: 100), ct);

        var queue = queueResult.Items.Select(a =>
        {
            var fullName = a.PatientFullName?.Trim() ?? string.Empty;
            var firstSpace = fullName.IndexOf(' ');
            var first = firstSpace > 0 ? fullName[..firstSpace] : fullName;
            var last = firstSpace > 0 ? fullName[(firstSpace + 1)..] : string.Empty;
            var legacyId = ToLegacyIntId(a.AppointmentId);

            return new
            {
                id = legacyId,
                appointment_guid = a.AppointmentId,
                patient_first_name = string.IsNullOrWhiteSpace(first) ? "Patient" : first,
                patient_last_name = string.IsNullOrWhiteSpace(last) ? "" : last,
                provider_name = a.ProviderName,
                specialty = "General Practice",
                start_time = a.AppointmentTime.ToString("HH:mm"),
                appointment_date = a.AppointmentTime.ToString("yyyy-MM-dd"),
                location = "Main Clinic",
                status = a.Status,
                checkout_status = a.Status == "arrived" ? "confirmed" : "searching",
                patient_email = "—",
                patient_phone = "—",
                patient_profile_id = ToLegacyIntId(a.PatientId),
                is_walk_in = a.IsWalkIn,
            };
        }).ToList();

        return Ok(new
        {
            success = true,
            data = new
            {
                queue,
                total = queue.Count,
            }
        });
    }

    [HttpPost("/api/staff/appointments/{appointmentId}/checkin")]
    public async Task<IActionResult> StaffCheckIn(string appointmentId, CancellationToken ct = default)
    {
        Guid appointmentGuid;
        if (Guid.TryParse(appointmentId, out var parsedGuid))
        {
            appointmentGuid = parsedGuid;
        }
        else if (int.TryParse(appointmentId, out var legacyId))
        {
            var queue = await _queue.GetQueueAsync(new QueueQuery(
                Date: null,
                Status: null,
                IsWalkIn: null,
                ProviderId: null,
                Page: 1,
                PageSize: 500), ct);

            var match = queue.Items.FirstOrDefault(x => ToLegacyIntId(x.AppointmentId) == legacyId);
            if (match is null)
            {
                return NotFound(new { success = false, error = new { message = "Appointment not found." } });
            }

            appointmentGuid = match.AppointmentId;
        }
        else
        {
            return BadRequest(new { success = false, error = new { message = "Invalid appointment ID." } });
        }

        CheckInResult result;
        try
        {
            result = await _queue.CheckInAsync(appointmentGuid, ct);
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new { success = false, error = new { message = ex.Message } });
        }

        return Ok(new
        {
            success = true,
            data = new
            {
                appointmentId,
                status = result.Status,
                arrivedAt = result.ArrivedAt,
            }
        });
    }

    [HttpGet("/api/staff/patients/search")]
    public async Task<IActionResult> StaffSearchPatients([FromQuery] string? query, [FromQuery] int take = 50, CancellationToken ct = default)
    {
        var q = (query ?? string.Empty).Trim();
        var safeTake = Math.Clamp(take, 1, 100);

        var dbItems = _sessions.SearchPatients(q, safeTake)
            .Select(p => new
            {
                id = p.PatientId,
                user_id = p.UserId,
                email = p.Email,
                role = p.Role,
                status = p.Status,
            })
            .ToList();

        var walkInMatches = q.Length >= 2
            ? await _walkIn.SearchPatientsAsync(new PatientSearchQuery(q, safeTake), ct)
            : [];

        var walkInItems = walkInMatches.Select(p => new
        {
            id = ToLegacyIntId(p.Id),
            user_id = p.FullName,
            email = p.Email ?? "—",
            role = "patient",
            status = "active",
        });

        var items = dbItems
            .Concat(walkInItems)
            .GroupBy(x => $"{x.user_id}|{x.email}", StringComparer.OrdinalIgnoreCase)
            .Select(g => g.First())
            .Take(safeTake)
            .ToList();

        return Ok(new
        {
            success = true,
            data = new
            {
                total = items.Count,
                items
            }
        });
    }

    [HttpGet("/api/auth/me")]
    public IActionResult Me()
    {
        var role = Request.Headers["X-Role"].FirstOrDefault() ?? "patient";
        return Ok(new
        {
            success = true,
            data = new
            {
                role,
                permissions = GetPermissions(role)
            }
        });
    }

    [HttpGet("/api/auth/{provider}/authorize")]
    public IActionResult AuthorizeCalendar(string provider)
    {
        if (!Integrations.ContainsKey(provider))
        {
            return NotFound(new { success = false, error = new { message = "Provider not supported" } });
        }

        return Ok(new
        {
            success = true,
            data = new
            {
                authorizeUrl = $"/api/auth/{provider}/callback"
            }
        });
    }

    [HttpGet("/api/auth/{provider}/callback")]
    public IActionResult CalendarCallback(string provider)
    {
        if (!Integrations.ContainsKey(provider))
        {
            return NotFound(new { success = false, error = new { message = "Provider not supported" } });
        }

        Integrations[provider] = new IntegrationState(true, "connected");
        return Ok(new
        {
            success = true,
            data = new
            {
                message = $"{provider} calendar connected.",
                integration = new
                {
                    google = Integrations["google"],
                    outlook = Integrations["outlook"]
                }
            }
        });
    }

    [HttpPost("/api/auth/{provider}/disconnect")]
    public IActionResult DisconnectCalendar(string provider)
    {
        if (!Integrations.ContainsKey(provider))
        {
            return NotFound(new { success = false, error = new { message = "Provider not supported" } });
        }

        Integrations[provider] = new IntegrationState(false, "revoked");
        return Ok(new
        {
            success = true,
            data = new
            {
                integration = new
                {
                    google = Integrations["google"],
                    outlook = Integrations["outlook"]
                }
            }
        });
    }

    [HttpGet("/api/clinical/thresholds")]
    public IActionResult GetThresholds()
    {
        return Ok(new
        {
            success = true,
            data = new
            {
                thresholds = new
                {
                    icd10 = new { value = Thresholds["icd10"], updatedBy = "system", changedAt = DateTimeOffset.UtcNow },
                    cpt = new { value = Thresholds["cpt"], updatedBy = "system", changedAt = DateTimeOffset.UtcNow }
                }
            }
        });
    }

    [HttpPut("/api/clinical/thresholds")]
    public IActionResult SaveThreshold([FromBody] SaveThresholdRequest req)
    {
        if (string.IsNullOrWhiteSpace(req.CodeType) || (req.CodeType != "icd10" && req.CodeType != "cpt"))
        {
            return BadRequest(new { success = false, error = "Unsupported code type." });
        }

        var value = req.ThresholdValue;
        if (value < 0 || value > 1)
        {
            return BadRequest(new { success = false, error = "Threshold value must be between 0 and 1." });
        }

        lock (ThresholdLock)
        {
            var oldValue = Thresholds[req.CodeType];
            Thresholds[req.CodeType] = value;
            ThresholdHistory.Insert(0, new ThresholdHistoryItem(req.CodeType, oldValue, value, req.UpdatedBy ?? "frontend_user", DateTimeOffset.UtcNow));
            if (ThresholdHistory.Count > 100)
            {
                ThresholdHistory.RemoveRange(100, ThresholdHistory.Count - 100);
            }
        }

        return Ok(new { success = true, data = new { message = "Threshold updated." } });
    }

    [HttpGet("/api/clinical/thresholds/history")]
    public IActionResult GetThresholdHistory()
    {
        lock (ThresholdLock)
        {
            return Ok(new
            {
                success = true,
                data = new
                {
                    history = ThresholdHistory.Select(h => new
                    {
                        codeType = h.CodeType,
                        oldValue = h.OldValue,
                        newValue = h.NewValue,
                        changedBy = h.ChangedBy,
                        changedAt = h.ChangedAt
                    }).ToList()
                }
            });
        }
    }

    [HttpPost("/api/clinical/conflicts/{conflictId:int}/resolve")]
    public IActionResult ResolveConflict(int conflictId)
    {
        return Ok(new { success = true, data = new { id = conflictId, resolved = true } });
    }

    [HttpGet("/api/clinical/patients/{patientId:int}/profile")]
    public IActionResult GetClinicalPatientProfile(int patientId)
    {
        return Ok(new
        {
            success = true,
            data = new
            {
                patientId,
                medications = new[]
                {
                    new { name = "Atorvastatin", dosage = "10mg", frequency = "Daily", conflictFlag = false },
                    new { name = "Metformin", dosage = "500mg", frequency = "Twice daily", conflictFlag = false },
                },
                allergies = new[]
                {
                    new { substance = "Penicillin", reaction = "Rash", severity = "high" }
                },
                diagnoses = new[]
                {
                    new { code = "I10", name = "Hypertension", diagnosedAt = DateTime.UtcNow.AddMonths(-8).ToString("yyyy-MM-dd") },
                    new { code = "E11.9", name = "Type 2 diabetes mellitus", diagnosedAt = DateTime.UtcNow.AddMonths(-3).ToString("yyyy-MM-dd") }
                },
                documents = new[]
                {
                    new { id = 1, file_name = "lab-panel.pdf", uploaded_at = DateTime.UtcNow.AddDays(-10).ToString("yyyy-MM-dd") }
                }
            }
        });
    }

    [HttpGet("/api/clinical/patients/{patientId:int}/conflicts")]
    public IActionResult GetClinicalPatientConflicts(int patientId)
    {
        return Ok(new
        {
            success = true,
            data = new
            {
                conflicts = new[]
                {
                    new
                    {
                        id = 1,
                        patientId,
                        type = "allergy",
                        message = "Potential allergy conflict requires review",
                        severity = "high",
                        status = "open"
                    }
                }
            }
        });
    }

    [HttpGet("/api/clinical/patients/{patientId:int}/suggestions")]
    public IActionResult GetClinicalPatientSuggestions(int patientId)
    {
        return Ok(new
        {
            success = true,
            data = new
            {
                suggestions = new[]
                {
                    new { id = 1, codeType = "icd10", code = "I10", description = "Essential (primary) hypertension", confidence = 0.94, status = "pending" },
                    new { id = 2, codeType = "cpt", code = "99213", description = "Office outpatient visit", confidence = 0.88, status = "pending" }
                }
            }
        });
    }

    [HttpPost("/api/clinical/patients/{patientId:int}/suggestions")]
    public IActionResult GenerateClinicalPatientSuggestions(int patientId)
    {
        return GetClinicalPatientSuggestions(patientId);
    }

    [HttpPost("/api/clinical/documents/upload")]
    public IActionResult UploadClinicalDocument([FromQuery] string? fileName)
    {
        var uploadedFile = Request.HasFormContentType ? Request.Form.Files.FirstOrDefault() : null;
        var resolvedFileName = !string.IsNullOrWhiteSpace(fileName)
            ? fileName
            : uploadedFile?.FileName;

        if (string.IsNullOrWhiteSpace(resolvedFileName))
        {
            resolvedFileName = "document.bin";
        }

        PatientDocumentItem created;
        lock (PatientDocumentsLock)
        {
            var nextId = PatientDocuments.Count == 0 ? 1 : PatientDocuments.Max(d => d.Id) + 1;
            created = new PatientDocumentItem(
                nextId,
                resolvedFileName,
                uploadedFile?.ContentType ?? "application/octet-stream",
                "complete",
                DateTimeOffset.UtcNow);
            PatientDocuments.Insert(0, created);
        }

        return Ok(new
        {
            success = true,
            data = new
            {
                id = created.Id,
                file_name = created.FileName,
                file_type = created.FileType,
                status = created.Status,
                uploaded_at = created.UploadedAt.ToString("yyyy-MM-dd HH:mm")
            }
        });
    }

    [HttpGet("/api/admin/users")]
    public IActionResult GetUsers()
    {
        var users = _sessions.GetManagedUsers();
        return Ok(new
        {
            success = true,
            data = users.Select(u => new
            {
                id = u.UserId,
                email = u.Email,
                role = u.Role,
                status = u.Status,
                createdAt = DateTimeOffset.UtcNow.AddDays(-7),
                created_at = DateTimeOffset.UtcNow.AddDays(-7)
            }).ToList()
        });
    }

    [HttpPost("/api/admin/users")]
    public IActionResult CreateUser([FromBody] CreateUserRequest? req)
    {
        var userId = req?.GetUserId();
        var role = req?.GetRole();
        if (string.IsNullOrWhiteSpace(userId) || string.IsNullOrWhiteSpace(role))
        {
            return BadRequest(new { success = false, error = new { message = "userId and role are required." } });
        }

        var (success, error) = _sessions.CreateManagedUser(
            userId,
            req?.GetEmail() ?? string.Empty,
            role,
            string.IsNullOrWhiteSpace(req?.Status) ? "active" : req.Status,
            req?.Password);

        if (!success)
        {
            return Conflict(new { success = false, error = new { message = error ?? "User already exists." } });
        }

        return Ok(new { success = true, data = new { id = userId } });
    }

    [HttpPatch("/api/admin/users/{userId}/role")]
    public IActionResult UpdateUserRole(string userId, [FromBody] UpdateRoleRequest req)
    {
        var (success, error, role) = _sessions.UpdateManagedUserRole(userId, req.Role);
        if (!success)
        {
            return NotFound(new { success = false, error = new { message = error ?? "User not found." } });
        }

        return Ok(new { success = true, data = new { id = userId, role } });
    }

    [HttpPatch("/api/admin/users/{userId}/status")]
    public IActionResult UpdateUserStatus(string userId, [FromBody] UpdateStatusRequest req)
    {
        var (success, error, status) = _sessions.UpdateManagedUserStatus(userId, req.Status);
        if (!success)
        {
            return NotFound(new { success = false, error = new { message = error ?? "User not found." } });
        }

        return Ok(new { success = true, data = new { id = userId, status } });
    }

    [HttpGet("/api/patient/appointments/upcoming")]
    public IActionResult GetUpcomingAppointments()
    {
        var today = DateTimeOffset.UtcNow.Date;
        var queue = _queue.GetQueueAsync(new QueueQuery(
            Date: null,
            Status: null,
            IsWalkIn: null,
            ProviderId: null,
            Page: 1,
            PageSize: 500)).GetAwaiter().GetResult();

        var items = queue.Items
            .Where(a => a.AppointmentTime.Date >= today)
            .OrderBy(a => a.AppointmentTime)
            .Select(a => new
            {
                id = ToLegacyIntId(a.AppointmentId),
                appointment_date = a.AppointmentTime.ToString("yyyy-MM-dd"),
                start_time = a.AppointmentTime.ToString("HH:mm"),
                end_time = a.AppointmentTime.AddMinutes(a.DurationMinutes).ToString("HH:mm"),
                provider_name = a.ProviderName,
                specialty = string.Empty,
                location = string.Empty,
                status = a.Status,
                can_reschedule = true,
                can_cancel = true
            })
            .ToList();

        return Ok(new { success = true, data = new { total = items.Count, items } });
    }

    [HttpGet("/api/patient/appointments/history")]
    public IActionResult GetAppointmentHistory()
    {
        var today = DateTimeOffset.UtcNow.Date;
        var queue = _queue.GetQueueAsync(new QueueQuery(
            Date: null,
            Status: null,
            IsWalkIn: null,
            ProviderId: null,
            Page: 1,
            PageSize: 500)).GetAwaiter().GetResult();

        var items = queue.Items
            .Where(a => a.AppointmentTime.Date < today)
            .OrderByDescending(a => a.AppointmentTime)
            .Select(a => new
            {
                id = ToLegacyIntId(a.AppointmentId),
                appointment_date = a.AppointmentTime.ToString("yyyy-MM-dd"),
                provider_name = a.ProviderName,
                specialty = string.Empty,
                status = a.Status,
                notes_available = false,
                notes_url = (string?)null,
                notes_unavailable_reason = "Clinical notes have not been released yet."
            })
            .ToList();

        return Ok(new { success = true, data = new { total = items.Count, items } });
    }

    [HttpGet("/api/patient/dashboard")]
    public IActionResult GetPatientDashboard()
    {
        var today = DateTimeOffset.UtcNow.Date;
        var queue = _queue.GetQueueAsync(new QueueQuery(
            Date: null,
            Status: null,
            IsWalkIn: null,
            ProviderId: null,
            Page: 1,
            PageSize: 500)).GetAwaiter().GetResult();

        var upcoming = queue.Items
            .Where(a => a.AppointmentTime.Date >= today)
            .OrderBy(a => a.AppointmentTime)
            .ToList();
        var past = queue.Items
            .Where(a => a.AppointmentTime.Date < today)
            .ToList();

        var upcomingCount = upcoming.Count;
        var pastCount = past.Count;
        var documentCount = PatientDocuments.Count;
        var healthItemCount = 0;

        var next = upcoming.FirstOrDefault();
        var nextAppointment = next is null
            ? null
            : new
            {
                provider_name = next.ProviderName,
                appointment_date = next.AppointmentTime.ToString("yyyy-MM-dd"),
                start_time = next.AppointmentTime.ToString("HH:mm"),
                location = string.Empty
            };

        return Ok(new
        {
            success = true,
            data = new
            {
                upcomingCount,
                pastCount,
                documentCount,
                healthItemCount,
                nextAppointment
            }
        });
    }

    [HttpGet("/api/patient/health-profile")]
    public IActionResult GetHealthProfile()
    {
        return Ok(new
        {
            success = true,
            data = new
            {
                medications = Array.Empty<object>(),
                allergies = Array.Empty<object>(),
                diagnoses = Array.Empty<object>(),
                chronic_conditions = Array.Empty<object>(),
                alerts = Array.Empty<object>(),
                version = 0,
                last_updated = DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm")
            }
        });
    }

    [HttpGet("/api/patient/documents")]
    public IActionResult GetPatientDocuments()
    {
        List<object> items;
        lock (PatientDocumentsLock)
        {
            items = PatientDocuments
                .Select(d => (object)new
                {
                    id = d.Id,
                    file_name = d.FileName,
                    file_type = d.FileType,
                    status = d.Status,
                    processing_status = d.Status,
                    uploaded_at = d.UploadedAt.ToString("yyyy-MM-dd HH:mm")
                })
                .ToList();
        }

        return Ok(new { success = true, data = new { total = items.Count, items } });
    }

    [HttpGet("/api/patient/notifications/preferences")]
    public IActionResult GetNotificationPreferences()
    {
        var patientId = Request.Headers["X-Patient-Id"].FirstOrDefault() ?? "1";
        var prefs = NotificationPrefsByPatient.GetOrAdd(patientId, _ => new NotificationPreferences(true, false, false));
        var channels = new List<string>();
        if (prefs.Email)
        {
            channels.Add("email");
        }
        if (prefs.Sms)
        {
            channels.Add("sms");
        }

        return Ok(new
        {
            success = true,
            data = new
            {
                channels,
                doNotDisturb = prefs.Do_not_disturb,
                email = prefs.Email,
                sms = prefs.Sms,
                do_not_disturb = prefs.Do_not_disturb
            }
        });
    }

    [HttpPut("/api/patient/notifications/preferences")]
    public IActionResult SaveNotificationPreferences([FromBody] SaveNotificationPreferencesRequest? req)
    {
        if (req is null)
        {
            return BadRequest(new { success = false, error = new { message = "Request body is required." } });
        }

        var channels = req.GetChannels();
        var resolved = new NotificationPreferences(
            channels.Contains("email", StringComparer.OrdinalIgnoreCase),
            channels.Contains("sms", StringComparer.OrdinalIgnoreCase),
            req.GetDoNotDisturb());

        var patientId = Request.Headers["X-Patient-Id"].FirstOrDefault() ?? "1";
        NotificationPrefsByPatient[patientId] = resolved;

        return Ok(new
        {
            success = true,
            data = new
            {
                channels,
                doNotDisturb = resolved.Do_not_disturb,
                email = resolved.Email,
                sms = resolved.Sms,
                do_not_disturb = resolved.Do_not_disturb
            }
        });
    }

    [HttpGet("/api/admin/filter-options")]
    public IActionResult GetAdminFilterOptions()
    {
        var queue = _queue.GetQueueAsync(new QueueQuery(
            Date: null,
            Status: null,
            IsWalkIn: null,
            ProviderId: null,
            Page: 1,
            PageSize: 500)).GetAwaiter().GetResult();

        var providers = queue.Items
            .Select(x => x.ProviderName)
            .Where(x => !string.IsNullOrWhiteSpace(x))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(x => x)
            .Select((name, idx) => new { id = (idx + 1).ToString(), name, credentials = string.Empty })
            .ToList();

        return Ok(new
        {
            success = true,
            data = new
            {
                providers
            }
        });
    }

    [HttpGet("/api/admin/operational-metrics")]
    public IActionResult GetAdminOperationalMetrics()
    {
        var queue = _queue.GetQueueAsync(new QueueQuery(
            Date: null,
            Status: null,
            IsWalkIn: null,
            ProviderId: null,
            Page: 1,
            PageSize: 500)).GetAwaiter().GetResult();

        var rows = queue.Items.ToList();
        var total = rows.Count;
        var booked = rows.Count(x => string.Equals(x.Status, "scheduled", StringComparison.OrdinalIgnoreCase) || string.Equals(x.Status, "arrived", StringComparison.OrdinalIgnoreCase));
        var cancelled = rows.Count(x => string.Equals(x.Status, "cancelled", StringComparison.OrdinalIgnoreCase));
        var available = Math.Max(0, total - booked - cancelled);
        var utilizationRate = total > 0 ? Math.Round((double)booked / total * 100, 1) : 0d;
        var noShowRate = total > 0 ? Math.Round((double)cancelled / total * 100, 1) : 0d;
        var avgWaitMinutes = rows.Count > 0 ? Math.Round(rows.Average(x => x.DurationMinutes), 1) : 0d;

        var byProvider = rows
            .GroupBy(x => x.ProviderName)
            .Select(g => new
            {
                providerName = g.Key,
                provider_name = g.Key,
                total = g.Count(),
                booked = g.Count(x => string.Equals(x.Status, "scheduled", StringComparison.OrdinalIgnoreCase) || string.Equals(x.Status, "arrived", StringComparison.OrdinalIgnoreCase)),
                available = 0,
                cancelled = g.Count(x => string.Equals(x.Status, "cancelled", StringComparison.OrdinalIgnoreCase))
            })
            .OrderByDescending(x => x.booked)
            .ToList();

        return Ok(new
        {
            success = true,
            data = new
            {
                utilizationRate,
                noShowRate,
                avgWaitMinutes,
                totalAppointments = total,
                byProvider,
                utilization_rate = utilizationRate,
                no_show_rate = noShowRate,
                avg_wait_minutes = avgWaitMinutes,
                total_appointments = total,
                last_updated = DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm"),
                by_provider = byProvider.Select(x => new { provider = x.providerName, count = x.booked })
            }
        });
    }

    [HttpGet("/api/admin/metrics/no-show")]
    public IActionResult GetNoShowMetrics()
    {
        var queue = _queue.GetQueueAsync(new QueueQuery(
            Date: null,
            Status: null,
            IsWalkIn: null,
            ProviderId: null,
            Page: 1,
            PageSize: 500)).GetAwaiter().GetResult();
        var rows = queue.Items.ToList();
        var total = rows.Count;
        var cancelled = rows.Count(x => string.Equals(x.Status, "cancelled", StringComparison.OrdinalIgnoreCase));
        var rate = total > 0 ? Math.Round((double)cancelled / total * 100, 1) : 0d;

        return Ok(new
        {
            success = true,
            data = new
            {
                noShowRate = rate,
                rate,
                delta = 0d
            }
        });
    }

    [HttpGet("/api/admin/metrics/wait-time")]
    public IActionResult GetWaitTimeMetrics()
    {
        var queue = _queue.GetQueueAsync(new QueueQuery(
            Date: null,
            Status: null,
            IsWalkIn: null,
            ProviderId: null,
            Page: 1,
            PageSize: 500)).GetAwaiter().GetResult();
        var waits = queue.Items.Select(x => x.DurationMinutes).OrderBy(x => x).ToList();
        var p95 = waits.Count == 0 ? 0 : waits[(int)Math.Min(waits.Count - 1, Math.Floor(waits.Count * 0.95))];

        return Ok(new
        {
            success = true,
            data = new
            {
                p95WaitMinutes = p95,
                p95_wait_minutes = p95,
                threshold_exceeded = p95 > 30
            }
        });
    }

    [HttpGet("/api/admin/metrics/utilization")]
    public IActionResult GetUtilizationMetrics() => Ok(new
    {
        success = true,
        data = new
        {
            bySpecialty = Array.Empty<object>(),
            by_specialty = Array.Empty<object>()
        }
    });

    [HttpGet("/api/admin/metrics/intake")]
    public IActionResult GetIntakeMetrics() => Ok(new
    {
        success = true,
        data = new
        {
            completionRate = 0d,
            intakeCompletionRate = 0d,
            completion_rate = 0,
            low_completion_flag = false
        }
    });

    [HttpGet("/api/admin/metrics/insurance")]
    public IActionResult GetInsuranceMetrics() => Ok(new { success = true, data = new { verified = 0, pending = 0, failed = 0, issue_flag = false } });

    [HttpGet("/api/admin/metrics/agreement")]
    public IActionResult GetAgreementMetrics() => Ok(new
    {
        success = true,
        data = new
        {
            agreementRate = 0d,
            byCategory = Array.Empty<object>(),
            agreement_rate = 0,
            by_category = Array.Empty<object>()
        }
    });

    [HttpGet("/api/admin/audit/events")]
    public IActionResult GetAdminAuditEvents(
        [FromQuery(Name = "event_type")] string? eventType,
        [FromQuery] string? actor,
        [FromQuery] string? from,
        [FromQuery] string? to,
        [FromQuery(Name = "page")] int page = 1,
        [FromQuery(Name = "page_size")] int pageSize = 50)
    {
        var normalizedPage = Math.Max(1, page);
        var normalizedSize = Math.Clamp(pageSize, 1, 100);

        IEnumerable<dynamic> filtered = AdminAuditEvents.Cast<dynamic>();

        if (!string.IsNullOrWhiteSpace(eventType))
        {
            filtered = filtered.Where(e => string.Equals((string?)e.eventType, eventType, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(actor))
        {
            filtered = filtered.Where(e => string.Equals((string?)e.actorId, actor, StringComparison.OrdinalIgnoreCase));
        }

        if (DateTimeOffset.TryParse(from, out var fromTs))
        {
            filtered = filtered.Where(e => (DateTimeOffset)e.timestamp >= fromTs);
        }

        if (DateTimeOffset.TryParse(to, out var toTs))
        {
            filtered = filtered.Where(e => (DateTimeOffset)e.timestamp <= toTs.AddDays(1));
        }

        var ordered = filtered.OrderByDescending(e => (DateTimeOffset)e.timestamp).ToList();
        var pageItems = ordered
            .Skip((normalizedPage - 1) * normalizedSize)
            .Take(normalizedSize)
            .Select(e => new
            {
                timestamp = ((DateTimeOffset)e.timestamp).ToString("O"),
                eventType = (string?)e.eventType,
                event_type = (string?)e.eventType,
                actorId = (string?)e.actorId,
                actor_id = (string?)e.actorId,
                message = (string?)e.message,
                details = e.details
            })
            .ToList();

        return Ok(new
        {
            success = true,
            data = new
            {
                events = pageItems,
                page = normalizedPage,
                pageSize = normalizedSize,
                total = ordered.Count
            }
        });
    }

    [HttpGet("/api/admin/change-log")]
    public IActionResult GetAdminChangeLog()
    {
        var entries = AdminAuditEvents
            .Cast<dynamic>()
            .OrderByDescending(e => (DateTimeOffset)e.timestamp)
            .Select(e => new
            {
                timestamp = ((DateTimeOffset)e.timestamp).ToString("O"),
                action = (string?)e.eventType,
                actor = (string?)e.actorId,
                message = (string?)e.message,
                details = e.details
            })
            .ToList();

        return Ok(new { success = true, data = new { entries } });
    }

    [HttpGet("/api/admin/audit/query/export")]
    public IActionResult ExportAdminAuditQuery()
    {
        var csv = new StringBuilder();
        csv.AppendLine("timestamp,event_type,actor_id,message");
        foreach (var e in AdminAuditEvents.Cast<dynamic>().OrderByDescending(x => (DateTimeOffset)x.timestamp))
        {
            csv.AppendLine($"{((DateTimeOffset)e.timestamp):O},{e.eventType},{e.actorId},\"{((string?)e.message ?? string.Empty).Replace("\"", "\"\"")}\"");
        }

        return File(Encoding.UTF8.GetBytes(csv.ToString()), "text/csv", $"audit_export_{DateTime.UtcNow:yyyy-MM-dd}.csv");
    }

    [HttpGet("/api/rbac/audit-log")]
    public IActionResult GetRbacAuditLog()
    {
        var entries = RbacAuditEvents
            .Cast<dynamic>()
            .OrderByDescending(e => (DateTimeOffset)e.timestamp)
            .Select(e => new
            {
                timestamp = ((DateTimeOffset)e.timestamp).ToString("O"),
                role = (string?)e.role,
                action = (string?)e.action,
                endpoint = (string?)e.endpoint,
                outcome = (string?)e.outcome
            })
            .ToList();

        return Ok(new { success = true, data = entries });
    }

    [HttpGet("/api/admin/metrics/export")]
    public IActionResult ExportMetrics()
    {
        var csv = new StringBuilder();
        csv.AppendLine("provider,appointments");
        csv.AppendLine("Dr. Morgan Lee,18");
        csv.AppendLine("Dr. Taylor Kim,24");
        return File(Encoding.UTF8.GetBytes(csv.ToString()), "text/csv", $"appointments_export_{DateTime.UtcNow:yyyy-MM-dd}.csv");
    }

    private static IReadOnlyList<string> GetPermissions(string role)
    {
        return role.ToLowerInvariant() switch
        {
            "admin" =>
            [
                "appointments:search",
                "appointments:view",
                "appointments:book",
                "appointments:checkout",
                "appointments:resend",
                "calendar:read",
                "integrations:connect",
                "integrations:disconnect",
                "clinical:view_profile",
                "clinical:upload_document",
                "clinical:process_document",
                "clinical:view_conflicts",
                "clinical:code_review",
                "clinical:manage_thresholds",
                "clinical:view_allergy_conflicts",
                "clinical:view_suggestions",
                "clinical:generate_suggestions",
                "clinical:resolve_conflict",
                "admin:dashboard",
                "admin:ops_jobs",
                "admin:audit_logs",
                "admin:user_management",
                "admin:change_log",
                "staff:queue_view",
                "staff:checkin"
            ],
            "staff" =>
            [
                "appointments:search",
                "appointments:view",
                "appointments:book",
                "appointments:checkout",
                "appointments:resend",
                "calendar:read",
                "clinical:view_profile",
                "clinical:upload_document",
                "clinical:process_document",
                "clinical:view_conflicts",
                "clinical:code_review",
                "clinical:view_allergy_conflicts",
                "clinical:view_suggestions",
                "clinical:generate_suggestions",
                "clinical:resolve_conflict",
                "admin:audit_logs",
                "staff:queue_view",
                "staff:checkin"
            ],
            _ =>
            [
                "appointments:search",
                "appointments:view",
                "appointments:book",
                "appointments:checkout",
                "calendar:read",
                "integrations:connect",
                "integrations:disconnect"
            ]
        };
    }

    public sealed record IntegrationState(bool Connected, string Status);
    public sealed record NotificationPreferences(bool Email, bool Sms, bool Do_not_disturb);
    public sealed record ThresholdHistoryItem(string CodeType, decimal OldValue, decimal NewValue, string ChangedBy, DateTimeOffset ChangedAt);
    public sealed record PatientDocumentItem(int Id, string FileName, string FileType, string Status, DateTimeOffset UploadedAt);

    private static int ToLegacyIntId(Guid id)
    {
        var bytes = id.ToByteArray();
        return Math.Abs(BitConverter.ToInt32(bytes, 0));
    }

    public sealed class SaveThresholdRequest
    {
        public string? CodeType { get; init; }
        public decimal ThresholdValue { get; init; }
        public string? UpdatedBy { get; init; }
        public string? Role { get; init; }
    }

    public sealed class SaveNotificationPreferencesRequest
    {
        public List<string>? Channels { get; init; }

        [JsonPropertyName("reminderChannels")]
        public List<string>? ReminderChannels { get; init; }

        [JsonPropertyName("doNotDisturb")]
        public bool? DoNotDisturb { get; init; }

        [JsonPropertyName("do_not_disturb")]
        public bool? DoNotDisturbSnakeCase { get; init; }

        public bool? Email { get; init; }
        public bool? Sms { get; init; }

        public List<string> GetChannels()
        {
            var source = Channels ?? ReminderChannels;
            if (source is { Count: > 0 })
            {
                return source
                    .Where(c => !string.IsNullOrWhiteSpace(c))
                    .Select(c => c.Trim().ToLowerInvariant())
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .ToList();
            }

            var derived = new List<string>();
            if (Email == true)
            {
                derived.Add("email");
            }
            if (Sms == true)
            {
                derived.Add("sms");
            }

            return derived;
        }

        public bool GetDoNotDisturb() => DoNotDisturb ?? DoNotDisturbSnakeCase ?? false;
    }

    public sealed class CreateUserRequest
    {
        [JsonPropertyName("userId")]
        public string? UserId { get; init; }

        [JsonPropertyName("user_id")]
        public string? UserIdSnakeCase { get; init; }

        [JsonPropertyName("id")]
        public string? Id { get; init; }

        public string? Email { get; init; }

        [JsonPropertyName("email_address")]
        public string? EmailAddress { get; init; }

        [JsonPropertyName("role")]
        public string? Role { get; init; }

        [JsonPropertyName("user_role")]
        public string? UserRole { get; init; }

        public string? Status { get; init; }
        public string? Password { get; init; }

        public string? GetUserId() =>
            !string.IsNullOrWhiteSpace(UserId) ? UserId
            : !string.IsNullOrWhiteSpace(UserIdSnakeCase) ? UserIdSnakeCase
            : Id;

        public string? GetRole() =>
            !string.IsNullOrWhiteSpace(Role) ? Role
            : UserRole;

        public string? GetEmail() =>
            !string.IsNullOrWhiteSpace(Email) ? Email
            : EmailAddress;
    }

    public sealed class UpdateRoleRequest
    {
        public string? Role { get; init; }
        public string? Reason { get; init; }
    }

    public sealed class UpdateStatusRequest
    {
        public string? Status { get; init; }
        public string? Reason { get; init; }
    }
}
