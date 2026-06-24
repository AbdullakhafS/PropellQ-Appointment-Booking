"""
EP-008 US-087: Stateless API — No Local Storage — Test Suite

QA-1  Local State Audit Tests          — no LOCAL_DISK state in registry
QA-2  Multi-Instance Routing Tests     — token validation is instance-agnostic
QA-3  Shared State Tests               — approved shared entries registered
QA-4  Failover Session Continuity      — token validation survives without local state
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.stateless_api import (
    APPROVED_STORAGE_TYPES,
    FORBIDDEN_STORAGE_TYPES,
    TRANSIENT_STORAGE_TYPES,
    CrossInstanceTokenValidator,
    ForbiddenLocalStateError,
    StateEntry,
    StateStorageType,
    StatelessAuditReport,
    StatelessAuditRunner,
    StatelessnessPolicy,
    _PROPELIQ_AUDIT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry(
    name: str = "store",
    storage_type: StateStorageType = StateStorageType.IN_MEMORY,
    owner_module: str = "src.example",
    is_shared: bool = False,
) -> StateEntry:
    return StateEntry(
        name=name,
        storage_type=storage_type,
        owner_module=owner_module,
        is_shared=is_shared,
    )


def _runner(*entries: StateEntry) -> StatelessAuditRunner:
    r = StatelessAuditRunner()
    for e in entries:
        r.register(e)
    return r


# ===========================================================================
# QA-1: Local State Audit Tests (BE-1)
# ===========================================================================


class TestStateStorageTypes:
    """QA-1 — StateStorageType enum and type sets are correctly defined."""

    def test_local_disk_is_forbidden(self):
        assert StateStorageType.LOCAL_DISK in FORBIDDEN_STORAGE_TYPES

    def test_database_is_approved(self):
        assert StateStorageType.DATABASE in APPROVED_STORAGE_TYPES

    def test_external_cache_is_approved(self):
        assert StateStorageType.EXTERNAL_CACHE in APPROVED_STORAGE_TYPES

    def test_in_memory_is_transient(self):
        assert StateStorageType.IN_MEMORY in TRANSIENT_STORAGE_TYPES

    def test_in_memory_not_forbidden(self):
        assert StateStorageType.IN_MEMORY not in FORBIDDEN_STORAGE_TYPES


class TestStatelessAuditRunner:
    """QA-1 — Audit runner detects LOCAL_DISK violations and classifies entries."""

    def test_empty_runner_is_compliant(self):
        runner = StatelessAuditRunner()
        report = runner.audit()
        assert report.is_compliant

    def test_in_memory_entry_not_a_violation(self):
        runner = _runner(_entry(storage_type=StateStorageType.IN_MEMORY))
        report = runner.audit()
        assert report.is_compliant
        assert len(report.violations) == 0

    def test_database_entry_not_a_violation(self):
        runner = _runner(_entry(storage_type=StateStorageType.DATABASE, is_shared=True))
        report = runner.audit()
        assert report.is_compliant

    def test_local_disk_entry_is_a_violation(self):
        runner = _runner(_entry(storage_type=StateStorageType.LOCAL_DISK))
        report = runner.audit()
        assert not report.is_compliant
        assert len(report.violations) == 1

    def test_multiple_local_disk_entries_all_flagged(self):
        runner = _runner(
            _entry("a", StateStorageType.LOCAL_DISK),
            _entry("b", StateStorageType.LOCAL_DISK),
        )
        report = runner.audit()
        assert len(report.violations) == 2

    def test_mixed_entries_only_violations_in_violations_list(self):
        runner = _runner(
            _entry("good", StateStorageType.DATABASE, is_shared=True),
            _entry("bad", StateStorageType.LOCAL_DISK),
        )
        report = runner.audit()
        assert len(report.violations) == 1
        assert report.violations[0].name == "bad"

    def test_approved_shared_entries_in_approved_list(self):
        runner = _runner(
            _entry("db", StateStorageType.DATABASE, is_shared=True),
            _entry("cache", StateStorageType.EXTERNAL_CACHE, is_shared=True),
        )
        report = runner.audit()
        assert len(report.approved) == 2

    def test_transient_in_memory_entries_in_transient_list(self):
        runner = _runner(_entry("session", StateStorageType.IN_MEMORY))
        report = runner.audit()
        assert len(report.transient) == 1

    def test_assert_no_violations_raises_on_forbidden(self):
        runner = _runner(_entry("disk_store", StateStorageType.LOCAL_DISK))
        with pytest.raises(ForbiddenLocalStateError) as exc_info:
            runner.assert_no_violations()
        assert "disk_store" in str(exc_info.value)

    def test_assert_no_violations_passes_when_compliant(self):
        runner = _runner(_entry("mem", StateStorageType.IN_MEMORY))
        runner.assert_no_violations()  # must not raise

    def test_audit_report_summary_is_compliant(self):
        runner = _runner(_entry(storage_type=StateStorageType.DATABASE, is_shared=True))
        summary = runner.audit().summary()
        assert summary["compliant"] is True
        assert summary["violations"] == 0

    def test_audit_report_summary_counts_total(self):
        runner = _runner(
            _entry("a"),
            _entry("b"),
            _entry("c"),
        )
        summary = runner.audit().summary()
        assert summary["total_entries"] == 3

    def test_audit_report_has_timestamp(self):
        report = StatelessAuditRunner().audit()
        assert report.audited_at is not None


class TestBuiltinAuditNoViolations:
    """QA-1 — PropelIQ's built-in audit runner has no LOCAL_DISK violations."""

    def test_propeliq_audit_is_compliant(self):
        report = _PROPELIQ_AUDIT.audit()
        assert report.is_compliant, (
            f"Unexpected LOCAL_DISK violations: {[e.name for e in report.violations]}"
        )

    def test_propeliq_audit_has_shared_database_entries(self):
        report = _PROPELIQ_AUDIT.audit()
        assert report.approved, "No approved shared-state entries registered"

    def test_propeliq_audit_has_transient_in_memory_entries(self):
        report = _PROPELIQ_AUDIT.audit()
        assert report.transient, "Expected some transient in-memory stores"

    def test_propeliq_assert_no_violations(self):
        _PROPELIQ_AUDIT.assert_no_violations()  # must not raise


# ===========================================================================
# QA-2: Multi-Instance Routing Tests (BE-2)
# ===========================================================================


class TestCrossInstanceTokenValidator:
    """QA-2 — CrossInstanceTokenValidator works without per-instance state."""

    def setup_method(self):
        self.validator = CrossInstanceTokenValidator()

    def test_valid_payload_returns_true(self):
        token = "token-abc"
        payload = {"user_id": "U1", "role": "staff"}
        assert self.validator.validate_stateless(token, payload) is True

    def test_empty_token_returns_false(self):
        assert self.validator.validate_stateless("", {"user_id": "U1", "role": "staff"}) is False

    def test_none_payload_returns_false(self):
        assert self.validator.validate_stateless("tok", None) is False

    def test_empty_payload_returns_false(self):
        assert self.validator.validate_stateless("tok", {}) is False

    def test_missing_role_returns_false(self):
        assert self.validator.validate_stateless("tok", {"user_id": "U1"}) is False

    def test_missing_user_id_returns_false(self):
        assert self.validator.validate_stateless("tok", {"role": "patient"}) is False

    def test_sub_claim_accepted_as_user_id(self):
        """JWT 'sub' claim treated as user_id alternative."""
        assert self.validator.validate_stateless("tok", {"sub": "U2", "role": "admin"}) is True

    def test_identical_result_across_two_validator_instances(self):
        """BE-2: any instance produces identical validation result for the same input."""
        token = "shared-token"
        payload = {"user_id": "U1", "role": "admin"}
        v1 = CrossInstanceTokenValidator()
        v2 = CrossInstanceTokenValidator()
        assert v1.validate_stateless(token, payload) == v2.validate_stateless(token, payload)

    def test_migration_description_contains_steps(self):
        migration = self.validator.describe_migration()
        assert len(migration["migration_steps"]) >= 4

    def test_migration_description_has_benefits(self):
        migration = self.validator.describe_migration()
        assert len(migration["benefits"]) >= 2

    def test_migration_not_yet_complete(self):
        assert self.validator.is_migration_complete() is False


# ===========================================================================
# QA-3: Shared State Tests (BE-3)
# ===========================================================================


class TestSharedStateClassification:
    """QA-3 — Required stateful data is registered with approved storage types."""

    def test_database_storage_is_shared(self):
        entry = _entry("appointments", StateStorageType.DATABASE, is_shared=True)
        assert entry.is_shared is True
        assert entry.storage_type in APPROVED_STORAGE_TYPES

    def test_external_cache_storage_is_shared(self):
        entry = _entry("sessions", StateStorageType.EXTERNAL_CACHE, is_shared=True)
        assert entry.is_shared is True
        assert entry.storage_type in APPROVED_STORAGE_TYPES

    def test_in_memory_storage_is_not_shared(self):
        entry = _entry("local_cache", StateStorageType.IN_MEMORY, is_shared=False)
        assert entry.is_shared is False

    def test_approved_entry_can_serve_any_instance(self):
        """Shared approved state is visible to all instances — statelessness preserved."""
        entry = StateEntry(
            name="appointments",
            storage_type=StateStorageType.DATABASE,
            owner_module="src.booking_service",
            is_shared=True,
        )
        runner = StatelessAuditRunner()
        runner.register(entry)
        report = runner.audit()
        assert entry in report.approved

    def test_statelessness_policy_approves_database_pattern(self):
        policy = StatelessnessPolicy()
        assert policy.is_pattern_approved(
            "Reading from shared SQLite/PostgreSQL database (is_shared=True)"
        )

    def test_statelessness_policy_approves_redis_pattern(self):
        policy = StatelessnessPolicy()
        assert policy.is_pattern_approved("Redis/Valkey for shared ephemeral state with TTL-backed keys")

    def test_statelessness_policy_rejects_local_disk_pattern(self):
        policy = StatelessnessPolicy()
        result = policy.is_pattern_approved("Writing user session data to local filesystem")
        assert result is False

    def test_statelessness_policy_rejects_local_session_dict(self):
        policy = StatelessnessPolicy()
        result = policy.is_pattern_approved(
            "Storing session tokens in instance-local dict without shared backing"
        )
        assert result is False


# ===========================================================================
# QA-4: Failover Session Continuity Tests
# ===========================================================================


class TestFailoverSessionContinuity:
    """QA-4 — Token validation survives scaling/failover without breakage."""

    def test_token_validation_stateless_no_store_lookup(self):
        """Stateless validation: new validator instance (simulating failover)
        can validate token from pre-parsed payload without consulting any store."""
        token = "abc123"
        payload = {"user_id": "U42", "role": "patient"}
        # Simulate failover: original instance died; new instance validates
        new_instance_validator = CrossInstanceTokenValidator()
        result = new_instance_validator.validate_stateless(token, payload)
        assert result is True

    def test_token_validation_consistent_across_restarts(self):
        """Same token → same validation result regardless of instance lifecycle."""
        token = "stable-token"
        payload = {"sub": "U99", "role": "admin"}
        results = [
            CrossInstanceTokenValidator().validate_stateless(token, payload)
            for _ in range(5)  # 5 simulated instances
        ]
        assert all(r is True for r in results)

    def test_invalid_token_consistently_rejected(self):
        """Invalid tokens are rejected on every instance."""
        results = [
            CrossInstanceTokenValidator().validate_stateless("", {})
            for _ in range(3)
        ]
        assert all(r is False for r in results)

    def test_audit_shows_no_new_local_disk_entries(self):
        """After statelessness refactor, no LOCAL_DISK entries should exist."""
        _PROPELIQ_AUDIT.assert_no_violations()

    def test_migration_path_documented(self):
        """BE-2: migration path from opaque UUIDs to signed tokens is described."""
        v = CrossInstanceTokenValidator()
        migration = v.describe_migration()
        assert "target_state" in migration
        assert "migration_steps" in migration
        assert len(migration["migration_steps"]) > 0


# ===========================================================================
# Documentation Review — STATELESSNESS_GUIDE.md
# ===========================================================================


class TestStatelessnessDocumentation:
    """QA-1/DOC-1 — STATELESSNESS_GUIDE.md exists and covers required topics."""

    @pytest.fixture
    def guide_text(self) -> str:
        guide = Path(__file__).resolve().parents[1] / "STATELESSNESS_GUIDE.md"
        assert guide.exists(), f"Guide not found at {guide}"
        return guide.read_text(encoding="utf-8")

    def test_guide_exists(self, guide_text):
        assert len(guide_text) > 300

    def test_guide_covers_prohibited_patterns(self, guide_text):
        assert "Prohibited" in guide_text

    def test_guide_covers_approved_patterns(self, guide_text):
        assert "Approved" in guide_text

    def test_guide_covers_migration_path(self, guide_text):
        assert "migration" in guide_text.lower() or "Migration" in guide_text

    def test_guide_covers_cross_instance_auth(self, guide_text):
        assert "cross" in guide_text.lower() or "instance" in guide_text.lower()

    def test_guide_covers_local_disk_prohibition(self, guide_text):
        assert "local" in guide_text.lower() and "disk" in guide_text.lower()

    def test_guide_covers_failover_continuity(self, guide_text):
        assert "failover" in guide_text.lower() or "session" in guide_text.lower()

    def test_guide_covers_ci_enforcement(self, guide_text):
        assert "ci" in guide_text.lower() or "assert" in guide_text.lower()
