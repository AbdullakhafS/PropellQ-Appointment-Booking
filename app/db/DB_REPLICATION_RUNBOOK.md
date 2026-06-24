# Database Replication Runbook

**Document ID:** RUN-DB-REPL-001  
**User Story:** US-084 (EP-008)  
**Task:** task_084 DOC-1  
**Version:** 1.0  
**Owner:** Database / Infrastructure Engineer  
**Status:** Approved  
**Effective Date:** 2026-06-24

---

## 1. Architecture Overview

PropelIQ uses a **primary + single standby** replication topology.  The standby receives a continuous stream of write-ahead log (WAL) segments from the primary and applies them asynchronously.

```
┌──────────────┐        WAL stream         ┌──────────────┐
│   PRIMARY    │ ─────────────────────────▶ │   STANDBY    │
│  (read/write)│                            │  (read-only) │
└──────┬───────┘                            └──────┬───────┘
       │ connection string                         │
       ▼                                           │ promoted on failover
┌──────────────┐                                   │
│  Application │ ◀─────── switch_primary() ────────┘
│  ConnectionRegistry                              
└──────────────┘
```

| Component | File |
|-----------|------|
| Replication manager | `app/src/replication_manager.py` |
| Lag monitoring | `ReplicationMonitor` class |
| Failover controller | `FailoverController` class |
| App connectivity | `ConnectionRegistry` class |
| Tests | `app/tests/test_replication_084.py` |

---

## 2. Roles and Responsibilities

| Role | Responsibility |
|------|----------------|
| Primary DBA | Owns replication configuration; approves promotion decisions |
| Secondary DBA / On-Call | Executes failover during incidents; monitors lag alerts |
| Operations Engineer | Monitors lag dashboards; escalates on CRITICAL alerts |
| Application Engineer | Updates `ConnectionRegistry` or connection-string secrets after promotion |
| QA Engineer | Runs failover drills (quarterly); validates runbook accuracy |

---

## 3. Replication Setup (DB-1)

### 3.1 Primary Configuration

```sql
-- PostgreSQL example (adapt for your platform)
-- Enable WAL-level replication
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 3;
ALTER SYSTEM SET wal_keep_size = '1GB';
ALTER SYSTEM SET synchronous_commit = 'local';  -- async replication; change to 'on' for sync

-- Create replication user
CREATE ROLE replicator REPLICATION LOGIN ENCRYPTED PASSWORD '<strong-password>';

SELECT pg_reload_conf();
```

`pg_hba.conf` entry to allow standby connection:
```
host  replication  replicator  <standby_ip>/32  md5
```

### 3.2 Standby Initialisation

```bash
# On the standby host
pg_basebackup \
  --host=<primary_host> \
  --port=5432 \
  --username=replicator \
  --pgdata=/var/lib/postgresql/data \
  --wal-method=stream \
  --checkpoint=fast \
  --progress

# Create standby signal
touch /var/lib/postgresql/data/standby.signal

# Configure recovery
cat >> /var/lib/postgresql/data/postgresql.conf <<EOF
primary_conninfo = 'host=<primary_host> port=5432 user=replicator password=<password>'
restore_command = ''
recovery_target_timeline = 'latest'
EOF

pg_ctl start
```

### 3.3 Verify Sync

```sql
-- On primary: confirm standby is streaming
SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn,
       (sent_lsn - replay_lsn) AS lag_bytes
FROM pg_stat_replication;
```

Expected output: `state = streaming`, `lag_bytes` near 0.

---

## 4. Replication Lag Monitoring (OPS-1)

### 4.1 Alert Thresholds

| Severity | Lag | Action |
|----------|-----|--------|
| WARNING | > 5 s | Investigate; check network, disk I/O, lock contention |
| CRITICAL | > 30 s | Page on-call DBA; prepare for failover |

These thresholds are configured via `LagThresholdPolicy` in `replication_manager.py`:

```python
from src.replication_manager import LagThresholdPolicy
policy = LagThresholdPolicy(warning_seconds=5.0, critical_seconds=30.0)
```

### 4.2 Monitoring Commands

```sql
-- Real-time lag (seconds) per standby
SELECT application_name,
       EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds
FROM pg_stat_replication;

-- On standby: confirm it is applying WAL
SELECT pg_is_in_recovery(),
       pg_last_wal_receive_lsn(),
       pg_last_wal_replay_lsn(),
       pg_last_xact_replay_timestamp();
```

### 4.3 Alert Routing

```
LagAlert (CRITICAL) → PagerDuty / CloudWatch Alarm → On-Call DBA
LagAlert (WARNING)  → Slack #db-ops channel
LagAlert (RESOLVED) → Slack #db-ops channel (auto-resolved)
```

---

## 5. Failover Procedure (DB-2)

### 5.1 Decision Checklist

Before promoting the standby, confirm:

- [ ] Primary is confirmed unavailable (ping + `pg_stat_replication` shows no `streaming` state).
- [ ] Standby is reachable (`ping <standby_host>`).
- [ ] Replication lag at last measurement — if > 30 s, data loss risk; confirm with stakeholder.
- [ ] No active write transactions on primary that have not yet replicated (check `pg_stat_replication.flush_lsn`).
- [ ] On-call DBA has approved promotion.

### 5.2 Failover Steps

#### Step 1 — Fence the old primary

Prevent split-brain by ensuring the old primary cannot accept writes:

```bash
# Option A: Stop PostgreSQL on old primary (if reachable)
ssh <primary_host> "pg_ctl stop -m fast -D /var/lib/postgresql/data"

# Option B: Revoke network access (security group / firewall rule)
# Block port 5432 to/from old primary at the cloud security group level.
```

#### Step 2 — Promote the standby

```bash
# On the standby host
pg_ctl promote -D /var/lib/postgresql/data
# OR: touch /tmp/postgresql.trigger.5432  (if trigger_file is configured)
```

Verify promotion:
```sql
-- On the new primary (former standby)
SELECT pg_is_in_recovery();  -- Must return 'f' (false)
SELECT pg_current_wal_lsn();
```

Using the Python manager (automated / drill path):
```python
from src.replication_manager import FailoverController
record = controller.promote_standby("standby-01", trigger="manual", notes="Primary disk failure")
print(f"Failover completed in {record.duration_seconds:.2f}s")
```

#### Step 3 — Update application connectivity (APP-1)

```python
from src.replication_manager import ConnectionRegistry
registry = ConnectionRegistry(host="<old_primary>", port=5432, database="propeliq")
registry.switch_primary(new_host="<standby_host>", new_port=5432)
# In production: write new_host to AWS SSM / Consul KV so all instances reload
```

Or update the environment variable / secrets manager entry:
```bash
# Kubernetes secret update
kubectl patch secret propeliq-db-secret \
  -p '{"stringData": {"DB_HOST": "<standby_host>"}}'
kubectl rollout restart deployment/propeliq-api
```

#### Step 4 — Validate new primary

```sql
-- Confirm writes succeed
INSERT INTO healthcheck_log (event, created_at) VALUES ('failover_validation', NOW());
SELECT * FROM healthcheck_log ORDER BY created_at DESC LIMIT 1;
```

#### Step 5 — Reconfigure replication (after old primary recovery)

Once the old primary is recovered, reconfigure it as the new standby:

```bash
# On old primary host (now acting as standby)
pg_basebackup --host=<new_primary> --port=5432 --username=replicator \
  --pgdata=/var/lib/postgresql/data_new --wal-method=stream --checkpoint=fast
# Swap data directories and start as standby (see Section 3.2)
```

### 5.3 Target Failover Timing

| Phase | Target Duration |
|-------|----------------|
| Detect + decision | < 2 minutes |
| Fence old primary | < 30 seconds |
| Promote standby | < 30 seconds |
| App connectivity switch | < 1 minute |
| Validate new primary | < 2 minutes |
| **Total end-to-end** | **< 6 minutes** |

---

## 6. Quarterly Failover Drill (QA-2)

Run a planned failover drill each quarter to validate timing and procedures:

1. **Schedule** — Announce maintenance window; notify all teams.
2. **Pre-drill** — Confirm lag = 0, backup completed, monitoring active.
3. **Initiate drill** — Call `promote_standby(trigger="drill")` (bypasses primary liveness check).
4. **Measure** — Record actual failover duration; compare to target (< 6 minutes).
5. **Validate** — Run integration tests against new primary; confirm app connectivity.
6. **Restore** — Failback to original primary topology (optional; may keep promoted standby).
7. **Document** — Update `FailoverRecord` and drill report; identify gaps.

```python
# Drill example
record = manager.promote(
    node_id="standby-01",
    trigger="drill",
    notes="Q3 2026 quarterly failover drill",
)
assert record.success is True
assert record.duration_seconds < 360  # 6 minutes
```

---

## 7. Backup Compatibility

Replication and backups must remain compatible:

- `pg_basebackup` runs against the primary; standby maintains a consistent replica.
- Do **not** run `pg_basebackup` directly against the standby unless `--target=standby` is set and the standby is confirmed up-to-date.
- After promotion, run a full `pg_basebackup` within 24 hours to establish a new backup baseline from the new primary.
- Restore from backup is tested via `app/src/restore_verification.py` — run this after any restore operation.

---

## 8. Recovery Validation Checklist (QA-4)

After any failover (planned or unplanned), complete this checklist before declaring recovery complete:

- [ ] `SELECT pg_is_in_recovery()` returns `f` on new primary.
- [ ] Application connectivity verified — at least one successful API call (`GET /health/ready` returns 200).
- [ ] Replication lag alert resolved — `ReplicationMonitor.get_alerts(AlertSeverity.CRITICAL)` empty.
- [ ] Backup taken from new primary within 24 hours.
- [ ] `FailoverRecord` created and stored in audit log.
- [ ] Stakeholders notified of RTO achieved and any data loss (RPO).
- [ ] Post-incident review scheduled within 5 business days.

---

## 9. Version History

| Version | Date | Author | Change Summary |
|---------|------|--------|----------------|
| 1.0 | 2026-06-24 | Database Engineer | Initial runbook — covers topology setup, lag monitoring, failover steps, quarterly drill, and recovery checklist. Implements US-084 DOC-1. |
