using System.Text.Json;

namespace PropelIQ.Api.Services;

public sealed class LegacyBookingStore
{
    private readonly object _lock = new();
    private readonly string _storePath;

    private Dictionary<string, ReservationRecord> _reservationsByToken = new(StringComparer.Ordinal);
    private HashSet<int> _bookedAppointmentIds = new();

    public LegacyBookingStore(IWebHostEnvironment environment)
    {
        var dataDir = Path.Combine(environment.ContentRootPath, "App_Data");
        Directory.CreateDirectory(dataDir);
        _storePath = Path.Combine(dataDir, "legacy-booking-store.json");
        Load();
    }

    public bool IsBooked(int appointmentId)
    {
        lock (_lock)
        {
            return _bookedAppointmentIds.Contains(appointmentId);
        }
    }

    public bool HasActiveReservation(int appointmentId, DateTimeOffset now)
    {
        lock (_lock)
        {
            PruneExpiredUnsafe(now);
            return _reservationsByToken.Values.Any(r => r.AppointmentId == appointmentId);
        }
    }

    public (string Token, DateTimeOffset ExpiresAt) CreateReservation(int appointmentId, DateTimeOffset now)
    {
        lock (_lock)
        {
            PruneExpiredUnsafe(now);

            var token = Guid.NewGuid().ToString("N");
            var expiresAt = now.AddSeconds(60);
            _reservationsByToken[token] = new ReservationRecord(appointmentId, expiresAt);
            SaveUnsafe();
            return (token, expiresAt);
        }
    }

    public (bool Success, int AppointmentId) ConsumeReservation(string token, DateTimeOffset now)
    {
        lock (_lock)
        {
            PruneExpiredUnsafe(now);

            if (!_reservationsByToken.TryGetValue(token, out var reservation))
            {
                return (false, 0);
            }

            _reservationsByToken.Remove(token);
            _bookedAppointmentIds.Add(reservation.AppointmentId);
            SaveUnsafe();
            return (true, reservation.AppointmentId);
        }
    }

    private void Load()
    {
        lock (_lock)
        {
            if (!File.Exists(_storePath))
            {
                return;
            }

            var json = File.ReadAllText(_storePath);
            var snapshot = JsonSerializer.Deserialize<StoreSnapshot>(json);
            if (snapshot is null)
            {
                return;
            }

            _reservationsByToken = snapshot.ReservationsByToken ?? new Dictionary<string, ReservationRecord>(StringComparer.Ordinal);
            _bookedAppointmentIds = snapshot.BookedAppointmentIds ?? new HashSet<int>();
        }
    }

    private void PruneExpiredUnsafe(DateTimeOffset now)
    {
        var expiredTokens = _reservationsByToken
            .Where(kvp => kvp.Value.ExpiresAt <= now)
            .Select(kvp => kvp.Key)
            .ToList();

        if (expiredTokens.Count == 0)
        {
            return;
        }

        foreach (var token in expiredTokens)
        {
            _reservationsByToken.Remove(token);
        }

        SaveUnsafe();
    }

    private void SaveUnsafe()
    {
        var snapshot = new StoreSnapshot(_reservationsByToken, _bookedAppointmentIds);
        var json = JsonSerializer.Serialize(snapshot, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(_storePath, json);
    }

    public sealed record ReservationRecord(int AppointmentId, DateTimeOffset ExpiresAt);

    public sealed record StoreSnapshot(
        Dictionary<string, ReservationRecord>? ReservationsByToken,
        HashSet<int>? BookedAppointmentIds);
}
