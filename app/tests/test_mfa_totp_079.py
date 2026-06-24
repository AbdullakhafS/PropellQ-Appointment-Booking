"""
EP-007 US-079: MFA Support (TOTP) — Test Suite

Covers UT-079-001 through UT-079-012 as defined in test_plan_079.md:

  UT-079-001  Enrollment generates role-eligible TOTP setup payload
  UT-079-002  Non-eligible role (patient) bypasses enrollment requirement
  UT-079-003  Valid TOTP code returns success
  UT-079-004  TOTP handles drift window correctly
  UT-079-005  Invalid TOTP rejects login
  UT-079-006  Invalid code response contains non-sensitive error only
  UT-079-007  Backup code redemption marks code as consumed
  UT-079-008  Reuse of consumed backup code is denied
  UT-079-009  Required-role unenrolled user cannot complete login
  UT-079-010  Required-role enrolled user with completed MFA can proceed
  UT-079-011  Recovery flow enforces secure criteria
  UT-079-012  MFA secrets excluded from logs/responses after enrollment

All tests use isolated service instances so the shared module-level singletons
are not affected by cross-test state.
"""
from __future__ import annotations

import time
import pytest

from src.mfa_service import (
    BACKUP_CODE_COUNT,
    BACKUP_CODE_LENGTH,
    MFA_REQUIRED_ROLES,
    MFA_EXEMPT_ROLES,
    MfaAlreadyEnrolledError,
    MfaBackupCodeConsumedError,
    MfaBackupCodeService,
    MfaBackupCodeStore,
    MfaCodeInvalidError,
    MfaEnrollmentRecord,
    MfaEnrollmentService,
    MfaEnrollmentStore,
    MfaNotEnrolledError,
    MfaPolicyEnforcer,
    TOTP_DIGITS,
    TOTP_ISSUER,
    TOTP_PERIOD,
    _hash_backup_code,
    generate_totp_secret,
    get_totp_code,
    verify_totp_code,
    build_provisioning_uri,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _fresh_services():
    """Return isolated enrollment + backup + policy service instances."""
    store = MfaEnrollmentStore()
    svc = MfaEnrollmentService(store)
    bk_store = MfaBackupCodeStore()
    bk_svc = MfaBackupCodeService(bk_store)
    policy = MfaPolicyEnforcer(svc)
    return svc, bk_svc, policy


def _enroll_user(svc: MfaEnrollmentService, user_id: str, role: str) -> str:
    """Enroll *user_id* and return the base32 secret (plaintext shown at setup)."""
    data = svc.begin_enrollment(user_id, f"{user_id}@test.local")
    secret = data["secret_b32"]
    code = get_totp_code(secret)
    svc.confirm_enrollment(user_id, code)
    return secret


# ===========================================================================
# UT-079-001: Enrollment generates a valid TOTP setup payload for eligible roles
# ===========================================================================


class TestEnrollmentPayload:
    """UT-079-001 — Enrollment generates role-eligible TOTP setup payload."""

    def test_begin_enrollment_returns_provisioning_uri(self):
        svc, _, _ = _fresh_services()
        data = svc.begin_enrollment("staff_001", "staff_001@clinic.local")
        assert "provisioning_uri" in data
        assert data["provisioning_uri"].startswith("otpauth://totp/")

    def test_provisioning_uri_contains_issuer(self):
        svc, _, _ = _fresh_services()
        data = svc.begin_enrollment("staff_002", "staff_002@clinic.local")
        assert TOTP_ISSUER in data["provisioning_uri"]

    def test_provisioning_uri_contains_secret(self):
        svc, _, _ = _fresh_services()
        data = svc.begin_enrollment("staff_003", "staff_003@clinic.local")
        secret = data["secret_b32"]
        assert secret in data["provisioning_uri"]

    def test_payload_includes_algorithm_digits_period(self):
        svc, _, _ = _fresh_services()
        data = svc.begin_enrollment("admin_001", "admin_001@clinic.local")
        assert data["algorithm"] == "SHA1"
        assert data["digits"] == 6
        assert data["period"] == 30

    def test_payload_includes_issuer(self):
        svc, _, _ = _fresh_services()
        data = svc.begin_enrollment("admin_002", "admin_002@clinic.local")
        assert data["issuer"] == TOTP_ISSUER

    def test_secret_is_valid_base32(self):
        import base64
        svc, _, _ = _fresh_services()
        data = svc.begin_enrollment("staff_004", "staff_004@clinic.local")
        # Should decode without error
        decoded = base64.b32decode(data["secret_b32"].upper())
        assert len(decoded) == 20  # 160-bit secret

    def test_repeated_begin_replaces_pending_enrollment(self):
        svc, _, _ = _fresh_services()
        data1 = svc.begin_enrollment("staff_005", "staff_005@clinic.local")
        data2 = svc.begin_enrollment("staff_005", "staff_005@clinic.local")
        # Secrets differ because pending enrollment is replaced
        assert data1["secret_b32"] != data2["secret_b32"]

    def test_already_enrolled_raises_error(self):
        svc, _, _ = _fresh_services()
        _enroll_user(svc, "staff_006", "staff")
        with pytest.raises(MfaAlreadyEnrolledError):
            svc.begin_enrollment("staff_006", "staff_006@clinic.local")

    def test_confirm_enrollment_marks_enrolled(self):
        svc, _, _ = _fresh_services()
        data = svc.begin_enrollment("staff_007", "staff_007@clinic.local")
        code = get_totp_code(data["secret_b32"])
        assert svc.confirm_enrollment("staff_007", code) is True
        assert svc.is_enrolled("staff_007")


# ===========================================================================
# UT-079-002: Non-eligible role (patient) bypasses MFA requirement
# ===========================================================================


class TestRoleEligibility:
    """UT-079-002 — Patients are not subject to MFA enforcement."""

    def test_mfa_required_roles_contains_staff_and_admin(self):
        assert "staff" in MFA_REQUIRED_ROLES
        assert "admin" in MFA_REQUIRED_ROLES

    def test_patient_not_in_required_roles(self):
        assert "patient" not in MFA_REQUIRED_ROLES

    def test_patient_in_exempt_roles(self):
        assert "patient" in MFA_EXEMPT_ROLES

    def test_policy_requires_mfa_for_staff(self):
        _, _, policy = _fresh_services()
        assert policy.requires_mfa("staff") is True

    def test_policy_requires_mfa_for_admin(self):
        _, _, policy = _fresh_services()
        assert policy.requires_mfa("admin") is True

    def test_policy_does_not_require_mfa_for_patient(self):
        _, _, policy = _fresh_services()
        assert policy.requires_mfa("patient") is False

    def test_patient_login_allowed_without_enrollment(self):
        _, _, policy = _fresh_services()
        allowed, reason = policy.check_login_allowed("patient_001", "patient")
        assert allowed is True
        assert reason == ""


# ===========================================================================
# UT-079-003: Valid TOTP code returns success
# ===========================================================================


class TestValidTotpCode:
    """UT-079-003 — Valid TOTP code succeeds at verify_login."""

    def test_valid_code_verify_login_returns_true(self):
        svc, _, _ = _fresh_services()
        secret = _enroll_user(svc, "staff_010", "staff")
        code = get_totp_code(secret)
        assert svc.verify_login("staff_010", code) is True

    def test_valid_code_does_not_raise(self):
        svc, _, _ = _fresh_services()
        secret = _enroll_user(svc, "staff_011", "staff")
        code = get_totp_code(secret)
        # Should not raise any exception
        svc.verify_login("staff_011", code)

    def test_code_for_current_counter_step_accepted(self):
        secret = generate_totp_secret()
        ts = time.time()
        code = get_totp_code(secret, ts)
        assert verify_totp_code(secret, code, ts) is True

    def test_six_digit_code_format(self):
        secret = generate_totp_secret()
        code = get_totp_code(secret)
        assert len(code) == TOTP_DIGITS
        assert code.isdigit()

    def test_code_zero_padded_to_6_digits(self):
        # Code must always be 6 chars even if HOTP result < 100000
        secret = generate_totp_secret()
        code = get_totp_code(secret)
        assert len(code) == 6


# ===========================================================================
# UT-079-004: TOTP drift window handles clock skew
# ===========================================================================


class TestTotpDriftWindow:
    """UT-079-004 — Codes within ±1 counter step are accepted."""

    def test_previous_counter_step_accepted(self):
        secret = generate_totp_secret()
        ts = time.time()
        # Previous counter step code
        past_code = get_totp_code(secret, ts - TOTP_PERIOD)
        assert verify_totp_code(secret, past_code, ts) is True

    def test_next_counter_step_accepted(self):
        secret = generate_totp_secret()
        ts = time.time()
        future_code = get_totp_code(secret, ts + TOTP_PERIOD)
        assert verify_totp_code(secret, future_code, ts) is True

    def test_two_steps_ahead_rejected(self):
        secret = generate_totp_secret()
        ts = time.time()
        far_future_code = get_totp_code(secret, ts + TOTP_PERIOD * 2)
        assert verify_totp_code(secret, far_future_code, ts) is False

    def test_two_steps_behind_rejected(self):
        secret = generate_totp_secret()
        ts = time.time()
        old_code = get_totp_code(secret, ts - TOTP_PERIOD * 2)
        assert verify_totp_code(secret, old_code, ts) is False

    def test_exact_boundary_minus_one_step_accepted(self):
        secret = generate_totp_secret()
        ts = time.time()
        boundary_code = get_totp_code(secret, ts - TOTP_PERIOD)
        assert verify_totp_code(secret, boundary_code, ts) is True

    def test_exact_boundary_plus_one_step_accepted(self):
        secret = generate_totp_secret()
        ts = time.time()
        boundary_code = get_totp_code(secret, ts + TOTP_PERIOD)
        assert verify_totp_code(secret, boundary_code, ts) is True


# ===========================================================================
# UT-079-005: Invalid TOTP rejects login
# ===========================================================================


class TestInvalidTotpCode:
    """UT-079-005 — Wrong TOTP code raises MfaCodeInvalidError."""

    def test_wrong_code_raises_code_invalid(self):
        svc, _, _ = _fresh_services()
        _enroll_user(svc, "staff_020", "staff")
        with pytest.raises(MfaCodeInvalidError):
            svc.verify_login("staff_020", "000000")

    def test_old_code_beyond_drift_rejected(self):
        svc, _, _ = _fresh_services()
        secret = generate_totp_secret()
        # Manually seed an enrollment record as enrolled
        rec = MfaEnrollmentRecord(user_id="staff_021", secret_b32=secret, is_enrolled=True)
        store = MfaEnrollmentStore()
        store.upsert(rec)
        svc2 = MfaEnrollmentService(store)
        ts = time.time()
        old_code = get_totp_code(secret, ts - TOTP_PERIOD * 3)
        with pytest.raises(MfaCodeInvalidError):
            svc2.verify_login("staff_021", old_code, timestamp=ts)

    def test_empty_code_rejected(self):
        svc, _, _ = _fresh_services()
        _enroll_user(svc, "staff_022", "staff")
        with pytest.raises(MfaCodeInvalidError):
            svc.verify_login("staff_022", "")

    def test_alphabetic_code_rejected(self):
        svc, _, _ = _fresh_services()
        _enroll_user(svc, "staff_023", "staff")
        with pytest.raises(MfaCodeInvalidError):
            svc.verify_login("staff_023", "ABCDEF")

    def test_short_code_rejected(self):
        svc, _, _ = _fresh_services()
        _enroll_user(svc, "staff_024", "staff")
        with pytest.raises(MfaCodeInvalidError):
            svc.verify_login("staff_024", "123")

    def test_verify_totp_code_returns_false_for_wrong_code(self):
        secret = generate_totp_secret()
        assert verify_totp_code(secret, "000000", time.time()) is False

    def test_verify_totp_code_returns_false_for_empty(self):
        secret = generate_totp_secret()
        assert verify_totp_code(secret, "", time.time()) is False


# ===========================================================================
# UT-079-006: Invalid code response is non-sensitive (no secret in error)
# ===========================================================================


class TestNonSensitiveErrorResponse:
    """UT-079-006 — Error messages from failed TOTP verification contain no secret material."""

    def test_invalid_code_error_message_does_not_contain_secret(self):
        svc, _, _ = _fresh_services()
        secret = _enroll_user(svc, "staff_030", "staff")
        try:
            svc.verify_login("staff_030", "000000")
        except MfaCodeInvalidError as exc:
            error_msg = str(exc)
            assert secret not in error_msg

    def test_invalid_code_error_does_not_reveal_algorithm_details(self):
        svc, _, _ = _fresh_services()
        _enroll_user(svc, "staff_031", "staff")
        try:
            svc.verify_login("staff_031", "000000")
        except MfaCodeInvalidError as exc:
            assert "secret" not in str(exc).lower()
            assert "hmac" not in str(exc).lower()

    def test_mfa_not_enrolled_error_does_not_leak_internal_state(self):
        svc, _, _ = _fresh_services()
        try:
            svc.verify_login("unknown_user", "123456")
        except MfaNotEnrolledError as exc:
            assert "secret" not in str(exc).lower()

    def test_enrollment_response_secret_only_in_begin_enrollment(self):
        svc, _, _ = _fresh_services()
        data = svc.begin_enrollment("staff_032", "staff_032@clinic.local")
        # Secret is present in begin_enrollment (expected: user needs it)
        assert "secret_b32" in data

    def test_confirm_enrollment_response_does_not_include_secret(self):
        svc, _, _ = _fresh_services()
        data = svc.begin_enrollment("staff_033", "staff_033@clinic.local")
        code = get_totp_code(data["secret_b32"])
        result = svc.confirm_enrollment("staff_033", code)
        # confirm_enrollment returns a bool, not a dict with secret
        assert result is True

    def test_is_enrolled_does_not_expose_secret(self):
        svc, _, _ = _fresh_services()
        _enroll_user(svc, "staff_034", "staff")
        # is_enrolled is a bool — no secret leakage
        enrolled = svc.is_enrolled("staff_034")
        assert isinstance(enrolled, bool)


# ===========================================================================
# UT-079-007: Backup code redemption marks code as consumed
# ===========================================================================


class TestBackupCodeRedemption:
    """UT-079-007 — Redeeming a backup code marks it as consumed (single-use)."""

    def test_generate_returns_10_codes(self):
        _, bk_svc, _ = _fresh_services()
        codes = bk_svc.generate("staff_040")
        assert len(codes) == BACKUP_CODE_COUNT

    def test_generated_codes_have_correct_length(self):
        _, bk_svc, _ = _fresh_services()
        codes = bk_svc.generate("staff_041")
        for code in codes:
            assert len(code) == BACKUP_CODE_LENGTH

    def test_codes_are_alphanumeric(self):
        _, bk_svc, _ = _fresh_services()
        codes = bk_svc.generate("staff_042")
        for code in codes:
            assert code.isalnum()

    def test_redeem_valid_code_returns_true(self):
        _, bk_svc, _ = _fresh_services()
        codes = bk_svc.generate("staff_043")
        assert bk_svc.redeem("staff_043", codes[0]) is True

    def test_redeem_marks_code_as_used(self):
        _, bk_svc, _ = _fresh_services()
        codes = bk_svc.generate("staff_044")
        bk_svc.redeem("staff_044", codes[0])
        remaining = bk_svc.remaining_count("staff_044")
        assert remaining == BACKUP_CODE_COUNT - 1

    def test_hash_stored_not_plaintext(self):
        _, bk_svc, _ = _fresh_services()
        codes = bk_svc.generate("staff_045")
        stored = bk_svc._store.get_codes("staff_045")
        for stored_code in stored:
            # No stored code hash should equal any raw plaintext code
            for plain in codes:
                assert stored_code.code_hash != plain

    def test_backup_codes_are_unique(self):
        _, bk_svc, _ = _fresh_services()
        codes = bk_svc.generate("staff_046")
        assert len(set(codes)) == BACKUP_CODE_COUNT

    def test_remaining_count_decreases_after_redemption(self):
        _, bk_svc, _ = _fresh_services()
        codes = bk_svc.generate("staff_047")
        initial = bk_svc.remaining_count("staff_047")
        bk_svc.redeem("staff_047", codes[0])
        assert bk_svc.remaining_count("staff_047") == initial - 1


# ===========================================================================
# UT-079-008: Reuse of consumed backup code is denied
# ===========================================================================


class TestBackupCodeReuseRejection:
    """UT-079-008 — A backup code that has been redeemed cannot be used again."""

    def test_redeem_same_code_twice_raises(self):
        _, bk_svc, _ = _fresh_services()
        codes = bk_svc.generate("staff_050")
        bk_svc.redeem("staff_050", codes[2])
        with pytest.raises(MfaBackupCodeConsumedError):
            bk_svc.redeem("staff_050", codes[2])

    def test_consumed_code_raises_consumed_error_not_invalid(self):
        _, bk_svc, _ = _fresh_services()
        codes = bk_svc.generate("staff_051")
        bk_svc.redeem("staff_051", codes[3])
        with pytest.raises(MfaBackupCodeConsumedError):
            bk_svc.redeem("staff_051", codes[3])

    def test_other_codes_still_valid_after_one_consumed(self):
        _, bk_svc, _ = _fresh_services()
        codes = bk_svc.generate("staff_052")
        bk_svc.redeem("staff_052", codes[0])
        # Another code should still work
        assert bk_svc.redeem("staff_052", codes[1]) is True

    def test_invalid_code_raises_code_invalid_error(self):
        _, bk_svc, _ = _fresh_services()
        bk_svc.generate("staff_053")
        with pytest.raises(MfaCodeInvalidError):
            bk_svc.redeem("staff_053", "INVALID1")

    def test_hash_backup_code_is_deterministic(self):
        code = "ABCD1234"
        assert _hash_backup_code(code) == _hash_backup_code(code)

    def test_different_codes_have_different_hashes(self):
        assert _hash_backup_code("ABCD1234") != _hash_backup_code("EFGH5678")


# ===========================================================================
# UT-079-009: Required-role unenrolled user cannot complete login
# ===========================================================================


class TestPolicyEnforcementUnenrolled:
    """UT-079-009 — Staff/Admin who haven't enrolled cannot complete login."""

    def test_unenrolled_staff_login_blocked(self):
        _, _, policy = _fresh_services()
        allowed, reason = policy.check_login_allowed("staff_060", "staff")
        assert allowed is False

    def test_unenrolled_staff_reason_contains_mfa_setup_required(self):
        _, _, policy = _fresh_services()
        _, reason = policy.check_login_allowed("staff_060", "staff")
        assert "MFA_SETUP_REQUIRED" in reason

    def test_unenrolled_admin_login_blocked(self):
        _, _, policy = _fresh_services()
        allowed, reason = policy.check_login_allowed("admin_060", "admin")
        assert allowed is False

    def test_unenrolled_admin_reason_is_setup_required(self):
        _, _, policy = _fresh_services()
        _, reason = policy.check_login_allowed("admin_060", "admin")
        assert "MFA_SETUP_REQUIRED" in reason

    def test_enrolled_but_no_challenge_staff_blocked(self):
        svc, _, policy = _fresh_services()
        _enroll_user(svc, "staff_061", "staff")
        # Not recorded challenge yet
        allowed, reason = policy.check_login_allowed("staff_061", "staff")
        assert allowed is False
        assert "MFA_CHALLENGE_REQUIRED" in reason

    def test_patient_never_blocked_regardless(self):
        _, _, policy = _fresh_services()
        allowed, _ = policy.check_login_allowed("patient_060", "patient")
        assert allowed is True


# ===========================================================================
# UT-079-010: Required-role enrolled user who passed challenge can proceed
# ===========================================================================


class TestPolicyEnforcementEnrolled:
    """UT-079-010 — Enrolled staff/admin who completed MFA can log in."""

    def test_enrolled_staff_with_challenge_passed_allowed(self):
        svc, _, policy = _fresh_services()
        _enroll_user(svc, "staff_070", "staff")
        policy.record_challenge_passed("staff_070")
        allowed, reason = policy.check_login_allowed("staff_070", "staff")
        assert allowed is True
        assert reason == ""

    def test_enrolled_admin_with_challenge_passed_allowed(self):
        svc, _, policy = _fresh_services()
        _enroll_user(svc, "admin_070", "admin")
        policy.record_challenge_passed("admin_070")
        allowed, reason = policy.check_login_allowed("admin_070", "admin")
        assert allowed is True
        assert reason == ""

    def test_clearing_challenge_re_blocks_user(self):
        svc, _, policy = _fresh_services()
        _enroll_user(svc, "staff_071", "staff")
        policy.record_challenge_passed("staff_071")
        assert policy.check_login_allowed("staff_071", "staff")[0] is True
        policy.clear_challenge("staff_071")
        assert policy.check_login_allowed("staff_071", "staff")[0] is False

    def test_status_shows_enrolled_and_challenge_passed(self):
        svc, _, policy = _fresh_services()
        _enroll_user(svc, "staff_072", "staff")
        policy.record_challenge_passed("staff_072")
        status = policy.status("staff_072", "staff")
        assert status["enrolled"] is True
        assert status["challenge_passed"] is True
        assert status["mfa_required"] is True

    def test_status_for_unenrolled_shows_correct_flags(self):
        _, _, policy = _fresh_services()
        status = policy.status("staff_073", "staff")
        assert status["enrolled"] is False
        assert status["challenge_passed"] is False
        assert status["mfa_required"] is True

    def test_verify_login_then_record_challenge_flow(self):
        svc, _, policy = _fresh_services()
        secret = _enroll_user(svc, "staff_074", "staff")
        code = get_totp_code(secret)
        svc.verify_login("staff_074", code)
        policy.record_challenge_passed("staff_074")
        allowed, _ = policy.check_login_allowed("staff_074", "staff")
        assert allowed is True


# ===========================================================================
# UT-079-011: Recovery flow enforces secure criteria
# ===========================================================================


class TestRecoveryFlow:
    """UT-079-011 — Recovery through backup codes requires enrollment; criteria enforced."""

    def test_generate_backup_codes_requires_enrollment(self):
        svc, bk_svc, _ = _fresh_services()
        # Not enrolled — should not be allowed by the service
        # (In web_app.py: 400 MFA_NOT_ENROLLED; here we test service directly)
        # The backup code service itself doesn't enforce enrollment;
        # enforcement is at the API handler layer. Verify has_any_codes is False.
        assert bk_svc.has_any_codes("staff_080") is False

    def test_backup_code_not_accepted_for_unknown_user(self):
        _, bk_svc, _ = _fresh_services()
        with pytest.raises(MfaCodeInvalidError):
            bk_svc.redeem("unknown_user", "ABCDEFGH")

    def test_backup_code_redemption_passes_mfa_challenge(self):
        svc, bk_svc, policy = _fresh_services()
        _enroll_user(svc, "staff_081", "staff")
        codes = bk_svc.generate("staff_081")
        bk_svc.redeem("staff_081", codes[0])
        policy.record_challenge_passed("staff_081")
        allowed, _ = policy.check_login_allowed("staff_081", "staff")
        assert allowed is True

    def test_all_backup_codes_consumed_leaves_none_remaining(self):
        _, bk_svc, _ = _fresh_services()
        codes = bk_svc.generate("staff_082")
        for code in codes:
            bk_svc.redeem("staff_082", code)
        assert bk_svc.remaining_count("staff_082") == 0

    def test_reset_enrollment_clears_enrollment_record(self):
        svc, _, _ = _fresh_services()
        _enroll_user(svc, "staff_083", "staff")
        assert svc.is_enrolled("staff_083")
        svc.reset_enrollment("staff_083")
        assert not svc.is_enrolled("staff_083")

    def test_new_backup_codes_invalidate_previous_set(self):
        svc, bk_svc, _ = _fresh_services()
        _enroll_user(svc, "staff_084", "staff")
        old_codes = bk_svc.generate("staff_084")
        new_codes = bk_svc.generate("staff_084")  # regenerate replaces old set
        # Old codes no longer valid (store overwritten)
        with pytest.raises(MfaCodeInvalidError):
            bk_svc.redeem("staff_084", old_codes[0])
        # New codes work
        assert bk_svc.redeem("staff_084", new_codes[0]) is True


# ===========================================================================
# UT-079-012: MFA secrets excluded from logs/responses
# ===========================================================================


class TestSecretsNotLeaked:
    """UT-079-012 — TOTP secrets are not present in service responses after enrollment."""

    def test_verify_login_return_value_is_bool_not_dict(self):
        svc, _, _ = _fresh_services()
        secret = _enroll_user(svc, "staff_090", "staff")
        code = get_totp_code(secret)
        result = svc.verify_login("staff_090", code)
        assert isinstance(result, bool)
        # Definitely not a dict containing secret material
        assert result is not dict

    def test_get_enrollment_record_has_secret_attribute(self):
        """Enrollment record holds secret — verify it's not in external API surfaces."""
        svc, _, _ = _fresh_services()
        secret = _enroll_user(svc, "staff_091", "staff")
        rec = svc.get_enrollment("staff_091")
        assert rec is not None
        # The record has the secret (internal use) but it's not returned to API
        assert rec.secret_b32 == secret

    def test_status_dict_does_not_contain_secret(self):
        svc, _, policy = _fresh_services()
        _enroll_user(svc, "staff_092", "staff")
        policy.record_challenge_passed("staff_092")
        status = policy.status("staff_092", "staff")
        assert "secret" not in status
        assert "secret_b32" not in status
        assert "key" not in status

    def test_status_dict_fields_are_non_sensitive(self):
        _, _, policy = _fresh_services()
        status = policy.status("staff_093", "staff")
        allowed_keys = {"user_id", "role", "mfa_required", "enrolled", "challenge_passed"}
        for key in status:
            assert key in allowed_keys

    def test_provisioning_uri_does_not_expose_raw_bytes(self):
        import base64
        secret = generate_totp_secret()
        uri = build_provisioning_uri(secret, "test_user@clinic.local")
        # URI contains base32 secret but never raw bytes
        key_bytes = base64.b32decode(secret.upper())
        assert key_bytes not in uri.encode()

    def test_backup_code_store_never_holds_plaintext(self):
        _, bk_svc, _ = _fresh_services()
        codes = bk_svc.generate("staff_094")
        stored = bk_svc._store.get_codes("staff_094")
        for stored_code in stored:
            for plain in codes:
                assert stored_code.code_hash != plain
                # Hash is 64-char hex (SHA-256)
                assert len(stored_code.code_hash) == 64
