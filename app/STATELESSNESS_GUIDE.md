# Statelessness Guide — API Design

**Document ID:** DOC-STATELESS-001  
**User Story:** US-087 (EP-008)  
**Version:** 1.0  
**Owner:** Backend / Platform Engineer  

---

## 1. Purpose

This guide defines the statelessness contract for the PropelIQ API.  It lists
prohibited patterns, approved alternatives, migration guidance, and the audit
tooling that enforces the policy programmatically.

**Goal:** Any API request can be served by any instance in the pool without
access to instance-local state.  This is a hard prerequisite for horizontal
scaling, zero-downtime deployments, and failover continuity.

---

## 2. Core Principle

> A stateless API stores **nothing per-instance** between requests.  Every
> piece of durable or shared state lives in an external service reachable by
> all instances equally.

---

## 3. Prohibited Patterns

The following patterns break statelessness.  They are detected by
`StatelessAuditRunner.assert_no_violations()` and must not appear in
production code.

| # | Prohibited Pattern | Why It Breaks Statelessness |
|---|-------------------|----------------------------|
| P-1 | Writing user session data to local filesystem | Only the instance that wrote the file can read it |
| P-2 | Opaque UUID session tokens in a module-level dict without shared backing | Token is unknown to all other instances |
| P-3 | Uploading files to local disk (`/tmp`, `./uploads`) | Files not visible to sibling instances |
| P-4 | Per-user preferences cached in a module-level dict | Preferences lost on restart; inconsistent across instances |
| P-5 | Workflow state persisted in a local SQLite file not accessible to peers | Resumable workflows siloed to one instance |

---

## 4. Approved Patterns

| # | Approved Pattern | `StateStorageType` |
|---|------------------|--------------------|
| A-1 | Shared SQLite / PostgreSQL for persistent records | `DATABASE` |
| A-2 | Redis / Valkey with TTL for shared ephemeral/session state | `EXTERNAL_CACHE` |
| A-3 | HMAC-SHA256 or JWT signed tokens (no server store needed for validation) | N/A (token-self-contained) |
| A-4 | Object storage (S3, Azure Blob) for uploaded files | `DATABASE` (treated as shared) |
| A-5 | Per-request in-memory computation discarded at response time | `IN_MEMORY` (transient, acceptable) |

---

## 5. Current State Audit (BE-1 / BE-3)

The `_PROPELIQ_AUDIT` singleton in `app/src/stateless_api.py` captures all
known state stores in the current codebase.

```python
from src.stateless_api import _PROPELIQ_AUDIT
report = _PROPELIQ_AUDIT.audit()
print(report.summary())
```

Expected output (brownfield baseline):

```json
{
  "compliant": true,
  "total_entries": 6,
  "violations": 0,
  "approved_shared_state": 2,
  "transient_in_memory": 4,
  "audited_at": "..."
}
```

**Interpretation:**

| Store | Type | Shared | Action Required |
|-------|------|--------|-----------------|
| `session_store` | IN_MEMORY | ✗ | Migrate to signed tokens (see §7) |
| `appointments` | DATABASE | ✓ | Already compliant |
| `audit_log` | DATABASE | ✓ | Already compliant |
| `mfa_enrollment_store` | IN_MEMORY | ✗ | Migrate to shared DB in next sprint |
| `mfa_backup_code_store` | IN_MEMORY | ✗ | Migrate to shared DB in next sprint |
| `admin_change_log` | IN_MEMORY | ✗ | Migrate to audit DB |

---

## 6. Cross-Instance Auth Consistency (BE-2)

### Current State

Session tokens are opaque UUIDs stored in `InMemorySessionStore` (per-instance).
A request authenticated on instance A **cannot** be validated on instance B.

This means the load balancer currently **must** use sticky sessions for auth
to work — but sticky sessions are disabled (`INFRA-3`).  The system is
currently single-instance only.

### Target State — Signed Tokens

```
Client                Instance A              Instance B
  │─── POST /api/auth/login ──────────────────►│
  │◄── {"token": "eyJ..."} ───────────────────│
  │                                            │
  │─── GET /api/appointments (Bearer eyJ...)───────────────►│
  │                    (no session lookup needed)           │
  │◄── 200 OK ──────────────────────────────────────────────│
```

The signed token embeds `user_id`, `role`, and `exp`.  Any instance verifies
the HMAC signature with the shared key and checks expiry — no store lookup.

### Migration Steps

See `CrossInstanceTokenValidator.describe_migration()` for the full step
breakdown.  Summary:

1. Embed `user_id`, `role`, `exp` in the token payload.
2. Sign with HMAC-SHA256 using a key from the secrets manager.
3. On validation: verify signature + expiry.  No store lookup.
4. Store revoked JTIs in shared Redis with TTL for logout support.
5. Rotate signing key via key versioning (`kid` header field).

---

## 7. Shared State Registry — Adding New Stores

When introducing any new state store, register it in `_PROPELIQ_AUDIT`:

```python
from src.stateless_api import _PROPELIQ_AUDIT, StateEntry, StateStorageType

_PROPELIQ_AUDIT.register(StateEntry(
    name="my_new_store",
    storage_type=StateStorageType.DATABASE,  # or EXTERNAL_CACHE
    owner_module="src.my_module",
    is_shared=True,
    description="Short description of what this state holds",
))
```

**Never register** a `LOCAL_DISK` entry — this will cause
`assert_no_violations()` to raise `ForbiddenLocalStateError` in CI.

---

## 8. Enforcement in CI

Add the following assertion to your integration test suite to prevent
regressions:

```python
from src.stateless_api import _PROPELIQ_AUDIT

def test_no_forbidden_local_state():
    _PROPELIQ_AUDIT.assert_no_violations()
```

This is already present in `app/tests/test_stateless_api_087.py`.

---

## 9. Failover Session Continuity (QA-4)

With the current opaque-UUID approach, sessions are **not** continuous across
failover.  Users must re-authenticate after instance failure.

With signed tokens (target state):

- Tokens are self-validating; no instance-specific state is required.
- Sessions survive any instance restart or failover as long as the token is
  unexpired.
- Revocation propagates to all instances via the shared Redis/DB revocation list.

---

## 10. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-06-24 | Initial guide. US-087 DOC-1. |
