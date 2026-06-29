using System.Collections.Concurrent;
using System.Security.Cryptography;
using Microsoft.EntityFrameworkCore;
using PropelIQ.Domain.Entities;
using PropelIQ.Infrastructure.Data;

namespace PropelIQ.Api.Services;

public sealed record SessionInfo(string UserId, string Role, string Email, DateTime ExpiresAt);
public sealed record ManagedUserInfo(string UserId, string Email, string Role, string Status);
public sealed record StaffPatientSearchResult(int PatientId, string UserId, string Email, string Role, string Status);

public sealed class SessionStore
{
    private readonly Dictionary<string, (string PasswordHash, string Role, string Email)> _demoUsers;
    private readonly ConcurrentDictionary<string, SessionInfo> _sessions = new();
    private readonly IServiceScopeFactory _scopeFactory;

    public SessionStore(IServiceScopeFactory scopeFactory)
    {
        _scopeFactory = scopeFactory;
        _demoUsers = new Dictionary<string, (string, string, string)>(StringComparer.OrdinalIgnoreCase)
        {
            ["admin1"]   = (HashPassword("Admin123!"),   "admin",   "admin@propellq.com"),
            ["staff1"]   = (HashPassword("Staff123!"),   "staff",   "staff@propellq.com"),
            ["patient1"] = (HashPassword("Patient123!"), "patient", "patient@propellq.com"),
        };

        SeedDemoUsers();
    }

    public SessionInfo? ValidateToken(string token)
    {
        if (_sessions.TryGetValue(token, out var session) && session.ExpiresAt > DateTime.UtcNow)
            return session;
        return null;
    }

    public (string? Token, string? Error) Login(string userId, string password)
    {
        if (!_demoUsers.TryGetValue(userId, out var entry))
        {
            using var scope = _scopeFactory.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            var persisted = db.AppUserAccounts.AsNoTracking().FirstOrDefault(u => u.UserId == userId);
            if (persisted is null)
            {
                return (null, "Invalid credentials.");
            }

            if (persisted.Status.Equals("inactive", StringComparison.OrdinalIgnoreCase))
            {
                return (null, "Account is inactive.");
            }

            entry = (persisted.PasswordHash, persisted.Role, persisted.Email);
        }

        if (!VerifyPassword(password, entry.PasswordHash))
            return (null, "Invalid credentials.");

        var token = Guid.NewGuid().ToString("N");
        _sessions[token] = new SessionInfo(userId, entry.Role, entry.Email, DateTime.UtcNow.AddHours(8));
        return (token, null);
    }

    public (bool Success, string? Error) Register(string userId, string email, string password)
    {
        if (_demoUsers.ContainsKey(userId))
            return (false, "User ID already taken.");

        if (password.Length < 8)
            return (false, "Password must be at least 8 characters.");

        using var scope = _scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        if (db.AppUserAccounts.Any(u => u.UserId == userId))
        {
            return (false, "User ID already taken.");
        }

        var now = DateTime.UtcNow;
        db.AppUserAccounts.Add(new AppUserAccount
        {
            UserId = userId,
            Email = email,
            PasswordHash = HashPassword(password),
            Role = "patient",
            Status = "active",
            CreatedAt = now,
            UpdatedAt = now
        });
        db.SaveChanges();

        return (true, null);
    }

    public IReadOnlyList<ManagedUserInfo> GetManagedUsers()
    {
        using var scope = _scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        return db.AppUserAccounts
            .AsNoTracking()
            .OrderBy(u => u.UserId)
            .Select(u => new ManagedUserInfo(u.UserId, u.Email, u.Role, u.Status))
            .ToList();
    }

    public IReadOnlyList<StaffPatientSearchResult> SearchPatients(string query, int take = 50)
    {
        using var scope = _scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();

        var q = (query ?? string.Empty).Trim();
        if (string.IsNullOrWhiteSpace(q))
        {
            return [];
        }

        var safeTake = Math.Clamp(take, 1, 100);
        return db.AppUserAccounts
            .AsNoTracking()
            .Where(u => u.Role == "patient"
                && (u.UserId.Contains(q) || u.Email.Contains(q)))
            .OrderBy(u => u.UserId)
            .Take(safeTake)
            .Select(u => new StaffPatientSearchResult(u.Id, u.UserId, u.Email, u.Role, u.Status))
            .ToList();
    }

    public (bool Success, string? Error) CreateManagedUser(string userId, string email, string role, string status, string? password = null)
    {
        if (_demoUsers.ContainsKey(userId))
        {
            return (false, "User ID already taken.");
        }

        using var scope = _scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        if (db.AppUserAccounts.Any(u => u.UserId == userId))
        {
            return (false, "User already exists.");
        }

        var finalPassword = string.IsNullOrWhiteSpace(password) ? "ChangeMe123!" : password;
        if (finalPassword.Length < 8)
        {
            return (false, "Password must be at least 8 characters.");
        }

        var now = DateTime.UtcNow;
        db.AppUserAccounts.Add(new AppUserAccount
        {
            UserId = userId,
            Email = email,
            PasswordHash = HashPassword(finalPassword),
            Role = role,
            Status = status,
            CreatedAt = now,
            UpdatedAt = now
        });
        db.SaveChanges();
        return (true, null);
    }

    public (bool Success, string? Error, string? Role) UpdateManagedUserRole(string userId, string? role)
    {
        using var scope = _scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        var user = db.AppUserAccounts.FirstOrDefault(u => u.UserId == userId);
        if (user is null)
        {
            return (false, "User not found.", null);
        }

        if (!string.IsNullOrWhiteSpace(role))
        {
            user.Role = role;
            user.UpdatedAt = DateTime.UtcNow;
            db.SaveChanges();
        }

        return (true, null, user.Role);
    }

    public (bool Success, string? Error, string? Status) UpdateManagedUserStatus(string userId, string? status)
    {
        using var scope = _scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        var user = db.AppUserAccounts.FirstOrDefault(u => u.UserId == userId);
        if (user is null)
        {
            return (false, "User not found.", null);
        }

        if (!string.IsNullOrWhiteSpace(status))
        {
            user.Status = status;
            user.UpdatedAt = DateTime.UtcNow;
            db.SaveChanges();
        }

        return (true, null, user.Status);
    }

    private void SeedDemoUsers()
    {
        try
        {
            using var scope = _scopeFactory.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            var now = DateTime.UtcNow;

            foreach (var (userId, entry) in _demoUsers)
            {
                var existing = db.AppUserAccounts.FirstOrDefault(u => u.UserId == userId);
                if (existing is null)
                {
                    db.AppUserAccounts.Add(new AppUserAccount
                    {
                        UserId = userId,
                        Email = entry.Email,
                        PasswordHash = entry.PasswordHash,
                        Role = entry.Role,
                        Status = "active",
                        CreatedAt = now,
                        UpdatedAt = now
                    });
                }
                else
                {
                    existing.Email = entry.Email;
                    existing.Role = entry.Role;
                    existing.PasswordHash = entry.PasswordHash;
                    existing.Status = "active";
                    existing.UpdatedAt = now;
                }
            }

            db.SaveChanges();
        }
        catch
        {
            // Startup should not fail if database is unavailable in non-DB scenarios.
        }
    }

    private static string HashPassword(string password)
    {
        var salt = RandomNumberGenerator.GetBytes(16);
        var hash = Rfc2898DeriveBytes.Pbkdf2(
            password, salt, 100_000, HashAlgorithmName.SHA256, 32);
        return $"{Convert.ToBase64String(salt)}:{Convert.ToBase64String(hash)}";
    }

    private static bool VerifyPassword(string password, string stored)
    {
        var parts = stored.Split(':');
        if (parts.Length != 2) return false;
        var salt = Convert.FromBase64String(parts[0]);
        var expected = Convert.FromBase64String(parts[1]);
        var actual = Rfc2898DeriveBytes.Pbkdf2(
            password, salt, 100_000, HashAlgorithmName.SHA256, 32);
        return CryptographicOperations.FixedTimeEquals(actual, expected);
    }
}
