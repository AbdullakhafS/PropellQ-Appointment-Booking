"""
EP-005 US-049: Password Reset Flow — Unit Tests

Covers:
  UT-US049-001  Reset request — privacy-safe endpoint, always generic response
  UT-US049-002  One-time expiring reset tokens
  UT-US049-003  Reset confirm — validation, policy enforcement, atomicity
  UT-US049-004  Rate limiting, security notifications, auditability
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.rbac import (
    _PASSWORD_RESET_AUDIT_LOG,
    _RATE_LIMIT_MAX_REQUESTS,
    _RATE_LIMIT_STORE,
    _RESET_TOKEN_STORE,
    _SECURITY_NOTIFICATIONS,
    _USER_ACTIVE_TOKEN,
    _USER_REGISTRY,
    confirm_password_reset,
    get_password_reset_audit_log,
    get_security_notifications,
    register_user,
    request_password_reset,
)


def _clear_reset_state():
    """Wipe all password-reset module state between tests."""
    _RESET_TOKEN_STORE.clear()
    _USER_ACTIVE_TOKEN.clear()
    _RATE_LIMIT_STORE.clear()
    _SECURITY_NOTIFICATIONS.clear()
    _PASSWORD_RESET_AUDIT_LOG.clear()
    _USER_REGISTRY.clear()


# =============================================================================
# UT-US049-001: Reset request endpoint — privacy-safe, always generic
# =============================================================================

class ResetRequestTests(unittest.TestCase):
    """Reset request always returns a generic response (task_049_001)."""

    def setUp(self):
        _clear_reset_state()
        register_user("staff-alice", "staff", "alice@clinic.example")

    def tearDown(self):
        _clear_reset_state()

    def test_nonexistent_user_returns_generic_success(self):
        result = request_password_reset("nobody@example.com")
        self.assertIn("message", result)
        self.assertIsNone(result["token"])
        self.assertFalse(result["rate_limited"])

    def test_valid_user_id_gets_token(self):
        result = request_password_reset("staff-alice")
        self.assertIsNotNone(result["token"])
        self.assertFalse(result["rate_limited"])

    def test_valid_email_gets_token(self):
        result = request_password_reset("alice@clinic.example")
        self.assertIsNotNone(result["token"])

    def test_inactive_user_no_token_but_generic_message(self):
        register_user("staff-bob", "staff", "bob@clinic.example", status="inactive")
        result = request_password_reset("staff-bob")
        self.assertIsNone(result["token"])
        self.assertFalse(result["rate_limited"])
        self.assertIn("if an account", result["message"].lower())

    def test_suspended_user_no_token_but_generic_message(self):
        register_user("staff-carol", "staff", "carol@clinic.example", status="suspended")
        result = request_password_reset("carol@clinic.example")
        self.assertIsNone(result["token"])
        self.assertIn("if an account", result["message"].lower())

    def test_message_is_identical_for_real_and_fake_users(self):
        result_real = request_password_reset("staff-alice")
        # Use a different identity key so rate-limit store doesn't interfere
        result_fake = request_password_reset("ghost@nowhere.example")
        self.assertEqual(result_real["message"], result_fake["message"])

    def test_new_request_invalidates_old_token(self):
        t1 = request_password_reset("staff-alice")["token"]
        # Clear rate-limit store so the second request is not blocked
        _RATE_LIMIT_STORE.clear()
        t2 = request_password_reset("staff-alice")["token"]
        self.assertNotEqual(t1, t2)
        self.assertNotIn(t1, _RESET_TOKEN_STORE)

    def test_nonexistent_user_logs_reset_no_user_event(self):
        request_password_reset("ghost@example.com")
        event_types = [e["event_type"] for e in get_password_reset_audit_log()]
        self.assertIn("reset_no_user", event_types)

    def test_valid_request_logs_token_issued_event(self):
        request_password_reset("staff-alice")
        event_types = [e["event_type"] for e in get_password_reset_audit_log()]
        self.assertIn("reset_token_issued", event_types)


# =============================================================================
# UT-US049-002: One-time expiring tokens
# =============================================================================

class TokenSecurityTests(unittest.TestCase):
    """Token entropy, expiry, and one-time-use guarantees (task_049_002)."""

    def setUp(self):
        _clear_reset_state()
        register_user("tok-user", "staff", "tok@clinic.example")

    def tearDown(self):
        _clear_reset_state()

    def test_token_has_sufficient_entropy(self):
        token = request_password_reset("tok-user")["token"]
        # secrets.token_urlsafe(32) produces ≥43 base64url characters
        self.assertGreaterEqual(len(token), 40)

    def test_tokens_are_unique_across_requests(self):
        t1 = request_password_reset("tok-user")["token"]
        _RATE_LIMIT_STORE.clear()
        t2 = request_password_reset("tok-user")["token"]
        self.assertNotEqual(t1, t2)

    def test_token_stored_with_all_required_fields(self):
        token = request_password_reset("tok-user")["token"]
        entry = _RESET_TOKEN_STORE[token]
        self.assertIn("user_id", entry)
        self.assertIn("expires_at", entry)
        self.assertIn("issued_at", entry)
        self.assertIn("used", entry)
        self.assertEqual(entry["user_id"], "tok-user")

    def test_expired_token_is_rejected(self):
        token = request_password_reset("tok-user")["token"]
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        _RESET_TOKEN_STORE[token]["expires_at"] = past
        ok, msg = confirm_password_reset(token, "ValidPass99!")
        self.assertFalse(ok)
        self.assertIn("invalid", msg.lower())

    def test_expired_token_is_removed_from_store(self):
        token = request_password_reset("tok-user")["token"]
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        _RESET_TOKEN_STORE[token]["expires_at"] = past
        confirm_password_reset(token, "ValidPass99!")
        self.assertNotIn(token, _RESET_TOKEN_STORE)

    def test_old_token_absent_from_store_after_new_request(self):
        t1 = request_password_reset("tok-user")["token"]
        self.assertIn(t1, _RESET_TOKEN_STORE)
        _RATE_LIMIT_STORE.clear()
        request_password_reset("tok-user")
        self.assertNotIn(t1, _RESET_TOKEN_STORE)


# =============================================================================
# UT-US049-003: Reset confirm endpoint
# =============================================================================

class ConfirmResetTests(unittest.TestCase):
    """Confirm endpoint: validation, policy, atomicity (task_049_003)."""

    def setUp(self):
        _clear_reset_state()
        register_user("conf-user", "staff", "conf@clinic.example")

    def tearDown(self):
        _clear_reset_state()

    def test_valid_token_and_password_succeeds(self):
        token = request_password_reset("conf-user")["token"]
        ok, result = confirm_password_reset(token, "SecurePass99!")
        self.assertTrue(ok)
        self.assertEqual(result, "conf-user")

    def test_password_hash_stored_after_successful_reset(self):
        token = request_password_reset("conf-user")["token"]
        confirm_password_reset(token, "SecurePass99!")
        self.assertIn("password_hash", _USER_REGISTRY["conf-user"])

    def test_token_removed_from_store_after_success(self):
        token = request_password_reset("conf-user")["token"]
        confirm_password_reset(token, "SecurePass99!")
        self.assertNotIn(token, _RESET_TOKEN_STORE)

    def test_token_unusable_after_successful_confirm(self):
        token = request_password_reset("conf-user")["token"]
        confirm_password_reset(token, "SecurePass99!")
        ok, msg = confirm_password_reset(token, "AnotherPass1!")
        self.assertFalse(ok)
        self.assertIn("invalid", msg.lower())

    def test_invalid_token_returns_safe_error(self):
        ok, msg = confirm_password_reset("not-a-real-token", "NewPass1!")
        self.assertFalse(ok)
        # Must not reveal whether the token ever existed
        self.assertNotIn("not found", msg.lower())
        self.assertIn("invalid", msg.lower())

    def test_password_too_short_is_rejected(self):
        token = request_password_reset("conf-user")["token"]
        ok, msg = confirm_password_reset(token, "short")
        self.assertFalse(ok)
        self.assertIn("characters", msg.lower())

    def test_empty_password_is_rejected(self):
        token = request_password_reset("conf-user")["token"]
        ok, msg = confirm_password_reset(token, "")
        self.assertFalse(ok)
        self.assertIn("empty", msg.lower())

    def test_confirm_logs_success_event(self):
        token = request_password_reset("conf-user")["token"]
        confirm_password_reset(token, "SecurePass99!")
        event_types = [e["event_type"] for e in get_password_reset_audit_log()]
        self.assertIn("reset_confirm_success", event_types)

    def test_expired_token_safe_error_message(self):
        token = request_password_reset("conf-user")["token"]
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        _RESET_TOKEN_STORE[token]["expires_at"] = past
        ok, msg = confirm_password_reset(token, "SecurePass99!")
        self.assertFalse(ok)
        # Error must not differentiate expired from never-issued
        self.assertIn("invalid", msg.lower())


# =============================================================================
# UT-US049-004 (rate limiting): Per-IP and per-identity throttling
# =============================================================================

class RateLimitingTests(unittest.TestCase):
    """Abuse-protection rate limits (task_049_004)."""

    def setUp(self):
        _clear_reset_state()

    def tearDown(self):
        _clear_reset_state()

    def test_ip_rate_limit_blocks_after_max_requests(self):
        for _ in range(_RATE_LIMIT_MAX_REQUESTS):
            result = request_password_reset("nobody", source_ip="1.2.3.4")
            self.assertFalse(result["rate_limited"])
        result = request_password_reset("nobody", source_ip="1.2.3.4")
        self.assertTrue(result["rate_limited"])

    def test_identity_rate_limit_blocks_after_max_requests(self):
        # Use unique IPs so IP rate limit is never hit
        for i in range(_RATE_LIMIT_MAX_REQUESTS):
            result = request_password_reset("target-id", source_ip=f"10.0.0.{i}")
            self.assertFalse(result["rate_limited"])
        # Same identity, fresh IP — identity limit now triggers
        result = request_password_reset("target-id", source_ip="10.1.1.1")
        self.assertTrue(result["rate_limited"])

    def test_rate_limited_response_still_generic(self):
        for _ in range(_RATE_LIMIT_MAX_REQUESTS):
            request_password_reset("nobody", source_ip="5.5.5.5")
        result = request_password_reset("nobody", source_ip="5.5.5.5")
        self.assertTrue(result["rate_limited"])
        # Message must not disclose rate-limit status
        self.assertIn("if an account", result["message"].lower())

    def test_different_ip_not_affected_by_another_ips_limit(self):
        # Exhaust IP 9.9.9.9 using distinct identities so the identity limit
        # for those keys isn't hit, only the IP limit for 9.9.9.9 is.
        for i in range(_RATE_LIMIT_MAX_REQUESTS):
            request_password_reset(f"user-drain-{i}", source_ip="9.9.9.9")
        # A completely different IP and identity must still be unrestricted
        result = request_password_reset("fresh-ident", source_ip="8.8.8.8")
        self.assertFalse(result["rate_limited"])

    def test_no_token_returned_when_rate_limited(self):
        for _ in range(_RATE_LIMIT_MAX_REQUESTS):
            request_password_reset("nobody", source_ip="2.2.2.2")
        result = request_password_reset("nobody", source_ip="2.2.2.2")
        self.assertIsNone(result["token"])

    def test_rate_limit_event_logged(self):
        for _ in range(_RATE_LIMIT_MAX_REQUESTS):
            request_password_reset("nobody", source_ip="3.3.3.3")
        request_password_reset("nobody", source_ip="3.3.3.3")
        event_types = [e["event_type"] for e in get_password_reset_audit_log()]
        self.assertIn("reset_rate_limited", event_types)


# =============================================================================
# UT-US049-004 (notifications + auditability)
# =============================================================================

class SecurityAuditTests(unittest.TestCase):
    """Security notifications and audit-log coverage (task_049_004)."""

    def setUp(self):
        _clear_reset_state()
        register_user("notif-user", "staff", "notif@clinic.example")

    def tearDown(self):
        _clear_reset_state()

    def test_notification_dispatched_on_reset_request(self):
        request_password_reset("notif-user")
        event_types = [n["event_type"] for n in get_security_notifications()]
        self.assertIn("password_reset_requested", event_types)

    def test_notification_dispatched_on_confirm_success(self):
        token = request_password_reset("notif-user")["token"]
        confirm_password_reset(token, "SecurePass99!")
        event_types = [n["event_type"] for n in get_security_notifications()]
        self.assertIn("password_reset_completed", event_types)

    def test_notification_includes_user_id_and_email(self):
        request_password_reset("notif-user")
        notifs = get_security_notifications()
        request_notif = next(
            n for n in notifs if n["event_type"] == "password_reset_requested"
        )
        self.assertEqual(request_notif["user_id"], "notif-user")
        self.assertEqual(request_notif["to"], "notif@clinic.example")

    def test_audit_log_entries_have_timestamp(self):
        request_password_reset("notif-user")
        log = get_password_reset_audit_log()
        self.assertGreaterEqual(len(log), 1)
        self.assertIn("timestamp", log[0])

    def test_audit_log_returned_newest_first(self):
        request_password_reset("notif-user")
        _RATE_LIMIT_STORE.clear()
        request_password_reset("notif-user")
        log = get_password_reset_audit_log()
        timestamps = [e["timestamp"] for e in log]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    def test_audit_log_covers_full_lifecycle(self):
        token = request_password_reset("notif-user")["token"]
        confirm_password_reset(token, "SecurePass99!")
        event_types = {e["event_type"] for e in get_password_reset_audit_log()}
        self.assertIn("reset_token_issued", event_types)
        self.assertIn("reset_confirm_success", event_types)

    def test_no_account_existence_disclosure_in_audit_for_nonexistent_user(self):
        request_password_reset("ghost@nowhere.example")
        log = get_password_reset_audit_log()
        event_types = [e["event_type"] for e in log]
        self.assertIn("reset_no_user", event_types)
        # Token issued event must NOT appear for a non-existent user
        self.assertNotIn("reset_token_issued", event_types)

    def test_notifications_and_audit_log_both_queryable(self):
        token = request_password_reset("notif-user")["token"]
        confirm_password_reset(token, "SecurePass99!")
        self.assertGreaterEqual(len(get_security_notifications()), 2)
        self.assertGreaterEqual(len(get_password_reset_audit_log()), 2)


if __name__ == "__main__":
    unittest.main()
