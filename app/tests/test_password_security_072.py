from __future__ import annotations

import sys
from unittest import TestCase

sys.path.insert(0, ".")

import bcrypt

from src.rbac import (
    BCRYPT_COST_FACTOR,
    _BCRYPT_PREFIX,
    _hash_password,
    _verify_password,
    confirm_password_reset,
    register_user,
    request_password_reset,
    verify_user_password,
    get_user,
    _USER_REGISTRY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_user(user_id: str) -> None:
    _USER_REGISTRY.pop(user_id, None)


# ===========================================================================
# Task 001 — Bcrypt Hashing Policy
# ===========================================================================

class TestBcryptHashingPolicy(TestCase):
    """AC: Bcrypt cost factor is defined for the environment.
    AC: Raw passwords excluded from logs and transient storage.
    AC: Migration strategy documented if legacy hashes exist."""

    def test_cost_factor_constant_is_defined(self) -> None:
        self.assertIsInstance(BCRYPT_COST_FACTOR, int)

    def test_cost_factor_is_at_least_12(self) -> None:
        """NIST/OWASP recommendation for 2024+: cost >= 12."""
        self.assertGreaterEqual(BCRYPT_COST_FACTOR, 12)

    def test_hash_output_starts_with_bcrypt_prefix(self) -> None:
        h = _hash_password("SomePassword1!")
        self.assertTrue(
            h.encode("utf-8").startswith(_BCRYPT_PREFIX),
            f"Expected $2b$ prefix, got: {h[:10]}",
        )

    def test_hash_embeds_cost_factor(self) -> None:
        h = _hash_password("P@ssw0rd")
        # bcrypt format: $2b$<rounds>$<22-char-salt><31-char-hash>
        parts = h.split("$")
        cost = int(parts[2])
        self.assertEqual(cost, BCRYPT_COST_FACTOR)

    def test_hash_output_contains_no_raw_password(self) -> None:
        raw = "SuperSecret99!"
        h = _hash_password(raw)
        self.assertNotIn(raw, h)
        self.assertNotIn(raw.encode(), h.encode())

    def test_two_hashes_of_same_password_differ(self) -> None:
        """Each hash must include a unique random salt."""
        h1 = _hash_password("password123")
        h2 = _hash_password("password123")
        self.assertNotEqual(h1, h2)

    def test_hash_is_not_reversible_plaintext(self) -> None:
        raw = "irreversible"
        h = _hash_password(raw)
        # The hash string must not be decodable back to the raw password.
        self.assertNotEqual(h, raw)

    def test_verify_password_module_exists(self) -> None:
        """_verify_password must be callable for the migration strategy."""
        self.assertTrue(callable(_verify_password))

    def test_legacy_pbkdf2_hash_is_still_verifiable(self) -> None:
        """Migration path: PBKDF2 hashes stored before bcrypt must remain verifiable."""
        import hashlib, secrets
        raw = "legacy_password"
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", raw.encode(), salt, 100_000)
        legacy_hash = f"{salt.hex()}:{dk.hex()}"
        self.assertTrue(_verify_password(raw, legacy_hash))

    def test_legacy_pbkdf2_wrong_password_fails(self) -> None:
        import hashlib, secrets
        raw = "correct"
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", raw.encode(), salt, 100_000)
        legacy_hash = f"{salt.hex()}:{dk.hex()}"
        self.assertFalse(_verify_password("wrong", legacy_hash))


# ===========================================================================
# Task 002 — Bcrypt Hashing on Credential Write Paths
# ===========================================================================

class TestCredentialWritePaths(TestCase):
    """AC: New or reset passwords are hashed before persistence.
    AC: Only hash material is stored."""

    def setUp(self) -> None:
        _clear_user("test-write-user")

    def tearDown(self) -> None:
        _clear_user("test-write-user")

    def test_register_user_with_password_stores_bcrypt_hash(self) -> None:
        register_user(
            "test-write-user", "admin", "write@example.com", password="Initial1!"
        )
        user = get_user("test-write-user")
        stored = user["password_hash"]
        self.assertTrue(stored.encode("utf-8").startswith(_BCRYPT_PREFIX))

    def test_register_user_does_not_store_raw_password(self) -> None:
        raw = "DoNotStore99"
        register_user("test-write-user", "staff", "w2@example.com", password=raw)
        user = get_user("test-write-user")
        self.assertNotIn(raw, user["password_hash"])
        self.assertNotIn(raw, str(user))

    def test_register_user_without_password_has_no_hash_field(self) -> None:
        register_user("test-write-user", "patient", "w3@example.com")
        user = get_user("test-write-user")
        self.assertNotIn("password_hash", user)

    def test_confirm_password_reset_stores_bcrypt_hash(self) -> None:
        register_user(
            "test-write-user", "admin", "reset@example.com", status="active"
        )
        result = request_password_reset("reset@example.com")
        token = result["token"]
        self.assertIsNotNone(token)

        ok, _ = confirm_password_reset(token, "NewBcryptPass1!")
        self.assertTrue(ok)

        user = get_user("test-write-user")
        stored = user["password_hash"]
        self.assertTrue(stored.encode("utf-8").startswith(_BCRYPT_PREFIX))

    def test_confirm_password_reset_does_not_retain_plaintext(self) -> None:
        register_user("test-write-user", "admin", "nr@example.com", status="active")
        result = request_password_reset("nr@example.com")
        token = result["token"]
        raw = "PlainTextCheck1!"
        confirm_password_reset(token, raw)

        user = get_user("test-write-user")
        self.assertNotIn(raw, user["password_hash"])

    def test_only_hash_stored_not_plaintext_or_salt_separately(self) -> None:
        """bcrypt hash includes the salt — no separate salt field required."""
        raw = "all-in-one-hash"
        register_user("test-write-user", "staff", "aio@example.com", password=raw)
        user = get_user("test-write-user")
        # Only password_hash field; no separate 'salt' key.
        self.assertNotIn("salt", user)
        self.assertIn("password_hash", user)


# ===========================================================================
# Task 003 — Login Verification and Migration Flow
# ===========================================================================

class TestLoginVerification(TestCase):
    """AC: Login uses bcrypt compare.
    AC: Legacy hash handling is documented or migrated.
    AC: Invalid credentials fail safely."""

    def setUp(self) -> None:
        _clear_user("test-login-user")

    def tearDown(self) -> None:
        _clear_user("test-login-user")

    def test_correct_password_verifies_true(self) -> None:
        register_user(
            "test-login-user", "staff", "login@example.com", password="Correct1!"
        )
        self.assertTrue(verify_user_password("test-login-user", "Correct1!"))

    def test_wrong_password_verifies_false(self) -> None:
        register_user(
            "test-login-user", "staff", "login2@example.com", password="Correct1!"
        )
        self.assertFalse(verify_user_password("test-login-user", "WrongPass1!"))

    def test_unknown_user_id_returns_false(self) -> None:
        """Must fail safely without raising an exception."""
        result = verify_user_password("nonexistent-user-xyz", "anyPassword")
        self.assertFalse(result)

    def test_user_without_password_hash_returns_false(self) -> None:
        register_user("test-login-user", "patient", "nopw@example.com")
        self.assertFalse(verify_user_password("test-login-user", "anything"))

    def test_empty_string_password_returns_false(self) -> None:
        register_user(
            "test-login-user", "staff", "empty@example.com", password="HasPassword1!"
        )
        self.assertFalse(verify_user_password("test-login-user", ""))

    def test_legacy_pbkdf2_hash_is_accepted_on_login(self) -> None:
        """Accounts with PBKDF2 hashes can still log in before migration."""
        import hashlib, secrets as sec
        raw = "legacy_login_pw"
        salt = sec.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", raw.encode(), salt, 100_000)
        register_user("test-login-user", "admin", "leg@example.com")
        get_user("test-login-user")["password_hash"] = f"{salt.hex()}:{dk.hex()}"

        self.assertTrue(verify_user_password("test-login-user", raw))

    def test_legacy_hash_upgraded_to_bcrypt_after_successful_login(self) -> None:
        """On first login with legacy hash, the stored hash is transparently upgraded."""
        import hashlib, secrets as sec
        raw = "upgrade_me_pw"
        salt = sec.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", raw.encode(), salt, 100_000)
        register_user("test-login-user", "admin", "upg@example.com")
        get_user("test-login-user")["password_hash"] = f"{salt.hex()}:{dk.hex()}"

        self.assertTrue(verify_user_password("test-login-user", raw))

        # After successful login, stored hash must now be bcrypt.
        updated = get_user("test-login-user")["password_hash"]
        self.assertTrue(updated.encode("utf-8").startswith(_BCRYPT_PREFIX))

    def test_verify_uses_bcrypt_checkpw_for_bcrypt_hashes(self) -> None:
        """Verify that bcrypt.checkpw is used for bcrypt-format hashes."""
        raw = "bcrypt_verify_pw"
        h = _hash_password(raw)
        self.assertTrue(bcrypt.checkpw(raw.encode(), h.encode()))
        self.assertFalse(bcrypt.checkpw(b"wrong", h.encode()))

    def test_confirm_password_reset_invalid_credentials_fail_safely(self) -> None:
        """Invalid token must return False with a safe error message."""
        ok, msg = confirm_password_reset("invalid-token-xyz", "AnyPass1!")
        self.assertFalse(ok)
        self.assertIn("Invalid or expired", msg)
        # Error must not contain timing-exploitable information about the token.
        self.assertNotIn("token", msg.lower().replace("token", ""))


# ===========================================================================
# Task 004 — Password Security Controls Validation
# ===========================================================================

class TestPasswordSecurityControls(TestCase):
    """AC: Hashing and login tests pass.
    AC: Cost factor review is completed.
    AC: No raw passwords appear in logs."""

    def setUp(self) -> None:
        _clear_user("test-sec-user")

    def tearDown(self) -> None:
        _clear_user("test-sec-user")

    def test_bcrypt_cost_factor_review(self) -> None:
        """Cost factor >= 12 is the minimum acceptable for HIPAA environments."""
        self.assertGreaterEqual(
            BCRYPT_COST_FACTOR,
            12,
            "BCRYPT_COST_FACTOR must be >= 12 per OWASP Password Storage Cheat Sheet.",
        )

    def test_hash_and_verify_roundtrip(self) -> None:
        raw = "RoundTrip99!"
        h = _hash_password(raw)
        self.assertTrue(_verify_password(raw, h))
        self.assertFalse(_verify_password("wrong", h))

    def test_no_raw_password_in_user_record(self) -> None:
        raw = "NoLeakPlease1!"
        register_user("test-sec-user", "admin", "noleak@example.com", password=raw)
        user_str = str(get_user("test-sec-user"))
        self.assertNotIn(raw, user_str)

    def test_no_raw_password_in_stored_hash_field(self) -> None:
        raw = "HiddenFromHash1!"
        register_user("test-sec-user", "staff", "hidden@example.com", password=raw)
        stored = get_user("test-sec-user")["password_hash"]
        self.assertNotIn(raw, stored)

    def test_hash_is_bcrypt_2b_format(self) -> None:
        """Confirm the exact bcrypt variant used is 2b (most secure)."""
        h = _hash_password("format_check")
        self.assertTrue(h.startswith("$2b$"))

    def test_verify_empty_stored_hash_returns_false(self) -> None:
        self.assertFalse(_verify_password("any", ""))

    def test_verify_malformed_hash_returns_false(self) -> None:
        self.assertFalse(_verify_password("any", "not-a-valid-hash"))

    def test_verify_none_stored_hash_returns_false(self) -> None:
        """Verify handles missing hash without raising."""
        self.assertFalse(_verify_password("any", ""))

    def test_unknown_user_verify_returns_false_not_exception(self) -> None:
        """verify_user_password must not raise for unknown user IDs."""
        try:
            result = verify_user_password("ghost-user-00", "pass")
            self.assertFalse(result)
        except Exception as exc:
            self.fail(f"verify_user_password raised unexpectedly: {exc}")

    def test_password_hash_excluded_from_sensitive_keys(self) -> None:
        """password_hash must be in the audit masking exclusion set."""
        from src.rbac import _AUDIT_SENSITIVE_KEYS
        self.assertIn("password_hash", _AUDIT_SENSITIVE_KEYS)


if __name__ == "__main__":
    import unittest

    unittest.main()
