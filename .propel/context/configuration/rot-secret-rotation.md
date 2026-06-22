# ROT-1: Secret Rotation and Revocation Procedure

**Status:** Published | **Version:** 1.0 | **Date:** 2026-06-22

---

## 1. Overview

Implement blue-green secret rotation flow where rotated secrets are consumed without code changes or service restart.

---

## 2. Blue-Green Rotation Pattern

```
Step 1: Create New Secret
  └─ Generate new password/key
  └─ Store in secret manager: version=2
  
Step 2: Service Loads New Secret
  └─ Background reload (every 5 min or on event)
  └─ In-memory cache updated
  └─ Old connection closed, new opened
  
Step 3: Verify New Secret Works
  └─ Test connection to database
  └─ Confirm queries succeed
  
Step 4: Mark Old Secret Deprecated
  └─ Set TTL on old secret (30 days)
  
Step 5: Delete Old Secret
  └─ After TTL expires, clean up
  
** Key: Service never restarted **
```

---

## 3. Implementation

### 3.1 C# Runtime Reload

```csharp
public class SecretRotationService : IHostedService
{
    private readonly ISecretManager _secretManager;
    private readonly IConnectionPool _connectionPool;
    private readonly ILogger _logger;
    private Timer _timer;
    
    public async Task StartAsync(CancellationToken cancellationToken)
    {
        // Check every 5 minutes
        _timer = new Timer(async _ => await CheckAndReloadSecretsAsync(), 
            null, TimeSpan.Zero, TimeSpan.FromMinutes(5));
    }
    
    private async Task CheckAndReloadSecretsAsync()
    {
        try
        {
            var currentVersion = await _secretManager.GetVersionAsync("db-password");
            var cachedVersion = _connectionPool.GetSecretVersion();
            
            if (currentVersion != cachedVersion)
            {
                _logger.LogInformation(
                    "Secret rotated: {Old} → {New}",
                    cachedVersion, currentVersion
                );
                
                // Load new secret
                var newPassword = await _secretManager.GetSecretAsync("db-password");
                
                // Update connection pool (blue-green)
                await _connectionPool.UpdateCredentialsAsync(newPassword);
                
                // Emit metric
                _telemetry.TrackSecretRotation("db-password", success: true);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Secret rotation check failed");
            _telemetry.TrackSecretRotation("db-password", success: false);
        }
    }
    
    public async Task StopAsync(CancellationToken cancellationToken)
    {
        _timer?.Dispose();
    }
}
```

### 3.2 Connection Pool Update

```csharp
public class ConnectionPool
{
    private string _currentPassword;
    private NpgsqlDataSource _dataSource;
    private string _secretVersion;
    
    public async Task UpdateCredentialsAsync(string newPassword)
    {
        // Create new connection string
        var connString = new NpgsqlConnectionStringBuilder(_originalConnString)
        {
            Password = newPassword
        }.ConnectionString;
        
        // Build new data source (blue)
        var newDataSource = NpgsqlDataSource.Create(connString);
        
        // Test new connection
        using (var conn = await newDataSource.OpenConnectionAsync())
        {
            await conn.ExecuteAsync("SELECT 1");  // Verify works
        }
        
        // Switch to new (green)
        var oldDataSource = _dataSource;
        _dataSource = newDataSource;
        _currentPassword = newPassword;
        
        // Dispose old connections
        oldDataSource?.Dispose();
        
        _logger.LogInformation("Connection pool updated with new credentials");
    }
}
```

---

## 4. Rotation Schedule

| Secret Type | Rotation Frequency | Trigger |
|---|---|---|
| Database password | Quarterly (90 days) | Scheduled |
| API keys | Bi-annually (180 days) | Scheduled |
| OAuth secrets | Annually (365 days) | Scheduled |
| Compromised secrets | Immediately | Manual |

---

## 5. Revocation Procedure

```
Compromised Secret Detected
  ↓
1. Create new secret immediately
2. Update secret manager (no TTL, active now)
3. Service loads new secret on next check (max 5 min)
4. Old secret version marked revoked
5. Audit log: "Secret revoked due to compromise"
6. Alert sent to security team
```

---

## 6. Rotation Audit Log

```
2026-06-22T14:30:00Z INFO Secret rotation: db-password
  Version: 1 → 2
  Triggered by: scheduled
  Status: success
  Duration: 45ms
  
2026-06-22T15:00:00Z INFO Connection pool updated
  Service: booking-service
  Old connections: 5 closed
  New connections: 0 (created on demand)
  
2026-06-22T15:00:05Z INFO Health check passed
  Database connection: healthy
  Query latency: 12ms
```

---

## 7. Testing Rotation

```csharp
[TestMethod]
public async Task RotateSecret_ServiceContinuesWorking()
{
    // Start service with secret v1
    var service = StartService();
    
    // Verify working
    var response1 = await service.GetAppointmentAsync(appointmentId);
    Assert.IsNotNull(response1);
    
    // Rotate secret (update secret manager to v2)
    await secretManager.RotateSecretAsync("db-password", newPassword);
    
    // Wait for service to reload (max 5 min, usually < 1 min)
    await Task.Delay(TimeSpan.FromSeconds(30));
    
    // Verify still working (no restart needed!)
    var response2 = await service.GetAppointmentAsync(appointmentId);
    Assert.IsNotNull(response2);
    
    // Verify old connections closed
    var oldConnections = await service.GetOldConnectionCountAsync();
    Assert.AreEqual(0, oldConnections);
}
```

---

## 8. Rollback Procedure

If rotation fails:

```
1. Secret manager still has old version
2. Revert service to use old version
3. Investigate why new secret failed
4. Fix issue and retry rotation
5. No service outage
```

---

## References

- AWS Secrets Manager Rotation: https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotation.html

**Next:** [AUDIT-1: Access and Change Audit Trail](audit-access-trail.md)
