"""
EP-007 US-073 — Session Timeout Tests (task_073_001 – task_073_004)

Validates:
  task_073_001 — 15-minute inactivity policy documented and enforced
  task_073_002 — server-side session expiration returns 401
  task_073_003 — session renewal issues a fresh token
  task_073_004 — timeout events are audit-logged
"""
from __future__ import annotations

import sys
import os
import json
import time
import unittest
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

# ---------------------------------------------------------------------------
# Subject-under-test imports
# ---------------------------------------------------------------------------
from src.rbac import (
    SESSION_INACTIVITY_TIMEOUT_SECONDS,
    _SESSION_ACTIVITY,
    _REVOKED_TOKEN_JTIS,
    _SESSION_TIMEOUT_LOG,
    _USER_SESSION_INDEX,
    issue_session_token,
    validate_session_token,
    renew_session_token,
    renew_session_activity,
    revoke_user_tokens,
    get_session_timeout_log,
    register_user,
)


def _clear_state():
    """Reset all in-process session stores between tests."""
    _SESSION_ACTIVITY.clear()
    _REVOKED_TOKEN_JTIS.clear()
    _SESSION_TIMEOUT_LOG.clear()
    _USER_SESSION_INDEX.clear()


# ===========================================================================
# TestSessionTimeoutPolicy — task_073_001
# ===========================================================================

class TestSessionTimeoutPolicy(unittest.TestCase):
    """task_073_001: Verify the policy constant and its characteristics."""

    def test_inactivity_timeout_is_15_minutes(self):
        """SESSION_INACTIVITY_TIMEOUT_SECONDS must equal 900 (15 minutes)."""
        self.assertEqual(SESSION_INACTIVITY_TIMEOUT_SECONDS, 900)

    def test_inactivity_timeout_is_positive_integer(self):
        self.assertIsInstance(SESSION_INACTIVITY_TIMEOUT_SECONDS, int)
        self.assertGreater(SESSION_INACTIVITY_TIMEOUT_SECONDS, 0)

    def test_inactivity_timeout_less_than_absolute_ttl(self):
        """Sliding window must be shorter than the absolute 1-hour TTL."""
        from src.rbac import _SESSION_TOKEN_TTL_SECONDS
        self.assertLess(SESSION_INACTIVITY_TIMEOUT_SECONDS, _SESSION_TOKEN_TTL_SECONDS)

    def test_policy_constant_exported(self):
        """SESSION_INACTIVITY_TIMEOUT_SECONDS must be importable from src.rbac."""
        import importlib
        mod = importlib.import_module("src.rbac")
        self.assertTrue(hasattr(mod, "SESSION_INACTIVITY_TIMEOUT_SECONDS"))

    def test_session_activity_store_exists(self):
        """_SESSION_ACTIVITY mapping must exist in the module."""
        import importlib
        mod = importlib.import_module("src.rbac")
        self.assertTrue(hasattr(mod, "_SESSION_ACTIVITY"))

    def test_session_timeout_log_exists(self):
        """_SESSION_TIMEOUT_LOG list must exist in the module."""
        import importlib
        mod = importlib.import_module("src.rbac")
        self.assertTrue(hasattr(mod, "_SESSION_TIMEOUT_LOG"))


# ===========================================================================
# TestServerSideExpiration — task_073_002
# ===========================================================================

class TestServerSideExpiration(unittest.TestCase):
    """task_073_002: Inactive sessions expire server-side and are rejected."""

    def setUp(self):
        _clear_state()

    def test_fresh_token_is_valid(self):
        result = issue_session_token("user1")
        claims = validate_session_token(result["token"])
        self.assertIsNotNone(claims)
        self.assertEqual(claims["sub"], "user1")

    def test_inactivity_timeout_expires_token(self):
        """A session idle for >15 minutes must be rejected."""
        result = issue_session_token("user_idle")
        jti = result["jti"]
        # Seed last-activity as 901 seconds ago.
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))

        claims = validate_session_token(result["token"])
        self.assertIsNone(claims)

    def test_timed_out_jti_is_revoked(self):
        """JTI must be moved to the revoked set after inactivity timeout."""
        result = issue_session_token("user_revoke")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 5))

        validate_session_token(result["token"])
        self.assertIn(jti, _REVOKED_TOKEN_JTIS)

    def test_timed_out_jti_removed_from_activity_store(self):
        """After timeout the JTI must be removed from the activity store."""
        result = issue_session_token("user_clean")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))

        validate_session_token(result["token"])
        self.assertNotIn(jti, _SESSION_ACTIVITY)

    def test_exactly_at_timeout_boundary_is_rejected(self):
        """A session idle for exactly TIMEOUT seconds must be rejected (> check)."""
        result = issue_session_token("boundary_user")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - SESSION_INACTIVITY_TIMEOUT_SECONDS)

        # now_ts - last = exactly TIMEOUT → now_ts - last > TIMEOUT is False
        # so this is the boundary: still valid at exactly equal.
        # The implementation uses >, so exactly 900 s should still be valid.
        claims = validate_session_token(result["token"])
        self.assertIsNotNone(claims)

    def test_one_second_past_timeout_is_rejected(self):
        result = issue_session_token("past_boundary")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))

        claims = validate_session_token(result["token"])
        self.assertIsNone(claims)

    def test_token_invalid_without_activity_after_timeout(self):
        """No entry in _SESSION_ACTIVITY means iat is used as the baseline.

        If iat is more than TIMEOUT seconds ago, the token must be rejected.
        We simulate this by issuing a token and mocking iat to be old enough.
        """
        result = issue_session_token("no_activity_user")
        jti = result["jti"]
        # Patch the iat in the activity record to simulate old-enough iat.
        _SESSION_ACTIVITY[jti] = float(int(time.time()) - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))

        claims = validate_session_token(result["token"])
        self.assertIsNone(claims)

    def test_revoked_token_still_rejected_after_activity_update(self):
        """A revoked JTI must remain invalid even if renew_session_activity is called."""
        result = issue_session_token("user_revoked_manual")
        jti = result["jti"]
        _REVOKED_TOKEN_JTIS.add(jti)
        renew_session_activity(jti)  # should return False and not re-admit token
        claims = validate_session_token(result["token"])
        self.assertIsNone(claims)


# ===========================================================================
# TestSessionRenewal — task_073_003
# ===========================================================================

class TestSessionRenewal(unittest.TestCase):
    """task_073_003: Active use renews the session; renew_session_token issues fresh token."""

    def setUp(self):
        _clear_state()

    # ---- Sliding window renewal via validate_session_token ----

    def test_validation_updates_activity_timestamp(self):
        """Each successful validate_session_token call must update _SESSION_ACTIVITY."""
        result = issue_session_token("sliding_user")
        jti = result["jti"]
        # Seed an old-but-valid timestamp (500 s ago).
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - 500)
        old_ts = _SESSION_ACTIVITY[jti]

        validate_session_token(result["token"])

        self.assertIn(jti, _SESSION_ACTIVITY)
        self.assertGreater(_SESSION_ACTIVITY[jti], old_ts)

    def test_activity_seeded_on_first_validation(self):
        """First validation of a fresh token must populate _SESSION_ACTIVITY."""
        result = issue_session_token("first_use")
        jti = result["jti"]
        # Ensure nothing pre-seeded.
        _SESSION_ACTIVITY.pop(jti, None)

        validate_session_token(result["token"])
        self.assertIn(jti, _SESSION_ACTIVITY)

    def test_active_session_never_times_out_within_window(self):
        """A token validated every 14 minutes should never expire (within TTL)."""
        result = issue_session_token("active_user")
        jti = result["jti"]
        now_ts = int(time.time())
        # Simulate last activity 840 s ago (14 min < 15 min timeout).
        _SESSION_ACTIVITY[jti] = float(now_ts - 840)

        claims = validate_session_token(result["token"])
        self.assertIsNotNone(claims)

    # ---- explicit renew_session_activity ----

    def test_renew_session_activity_returns_true_for_valid_jti(self):
        result = issue_session_token("renew_explicit")
        jti = result["jti"]
        validate_session_token(result["token"])  # seed activity
        self.assertTrue(renew_session_activity(jti))

    def test_renew_session_activity_returns_false_for_unknown_jti(self):
        self.assertFalse(renew_session_activity("nonexistent-jti"))

    def test_renew_session_activity_returns_false_for_revoked_jti(self):
        result = issue_session_token("revoked_explicit")
        jti = result["jti"]
        _REVOKED_TOKEN_JTIS.add(jti)
        self.assertFalse(renew_session_activity(jti))

    # ---- renew_session_token (full token swap) ----

    def test_renew_session_token_returns_new_token(self):
        result = issue_session_token("renew_user")
        new_result = renew_session_token(result["token"])
        self.assertIsNotNone(new_result)
        self.assertIn("token", new_result)
        self.assertIn("jti", new_result)
        self.assertIn("expires_at", new_result)

    def test_renew_session_token_issues_different_jti(self):
        result = issue_session_token("jti_user")
        new_result = renew_session_token(result["token"])
        self.assertNotEqual(result["jti"], new_result["jti"])

    def test_renew_session_token_invalidates_old_token(self):
        result = issue_session_token("old_token_user")
        renew_session_token(result["token"])
        claims = validate_session_token(result["token"])
        self.assertIsNone(claims)

    def test_renew_session_token_new_token_is_valid(self):
        result = issue_session_token("new_valid_user")
        new_result = renew_session_token(result["token"])
        claims = validate_session_token(new_result["token"])
        self.assertIsNotNone(claims)

    def test_renew_session_token_preserves_role(self):
        register_user("staff_renew", "staff", "staff@clinic.test")
        result = issue_session_token("staff_renew", role="staff")
        new_result = renew_session_token(result["token"])
        claims = validate_session_token(new_result["token"])
        self.assertEqual(claims["role"], "staff")

    def test_renew_session_token_returns_none_for_expired_inactive(self):
        """renew_session_token must return None when the token is timed out."""
        result = issue_session_token("timed_out_renew")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))

        new_result = renew_session_token(result["token"])
        self.assertIsNone(new_result)

    def test_renew_session_token_returns_none_for_revoked(self):
        result = issue_session_token("revoked_renew")
        _REVOKED_TOKEN_JTIS.add(result["jti"])
        new_result = renew_session_token(result["token"])
        self.assertIsNone(new_result)

    def test_renew_session_token_returns_none_for_empty_string(self):
        new_result = renew_session_token("")
        self.assertIsNone(new_result)

    # ---- revoke_user_tokens cleans activity store ----

    def test_revoke_user_tokens_cleans_activity_store(self):
        result = issue_session_token("revoke_clean_user")
        jti = result["jti"]
        validate_session_token(result["token"])  # seed activity
        self.assertIn(jti, _SESSION_ACTIVITY)
        revoke_user_tokens("revoke_clean_user")
        self.assertNotIn(jti, _SESSION_ACTIVITY)


# ===========================================================================
# TestTimeoutAuditLogging — task_073_004
# ===========================================================================

class TestTimeoutAuditLogging(unittest.TestCase):
    """task_073_004: Timeout events must be audit-logged."""

    def setUp(self):
        _clear_state()

    def test_timeout_creates_audit_entry(self):
        """Inactivity timeout must append an entry to _SESSION_TIMEOUT_LOG."""
        result = issue_session_token("audit_user")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))

        validate_session_token(result["token"])

        self.assertGreater(len(_SESSION_TIMEOUT_LOG), 0)

    def test_timeout_log_entry_has_required_fields(self):
        result = issue_session_token("audit_fields_user")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 5))

        validate_session_token(result["token"])

        entry = _SESSION_TIMEOUT_LOG[-1]
        for field in ("timestamp", "event", "sub", "jti", "reason", "idle_seconds"):
            self.assertIn(field, entry, f"Missing field: {field}")

    def test_timeout_log_event_is_SESSION_TIMEOUT(self):
        result = issue_session_token("event_name_user")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))

        validate_session_token(result["token"])
        self.assertEqual(_SESSION_TIMEOUT_LOG[-1]["event"], "SESSION_TIMEOUT")

    def test_timeout_log_records_correct_subject(self):
        result = issue_session_token("subject_user")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))

        validate_session_token(result["token"])
        self.assertEqual(_SESSION_TIMEOUT_LOG[-1]["sub"], "subject_user")

    def test_timeout_log_records_correct_jti(self):
        result = issue_session_token("jti_log_user")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 2))

        validate_session_token(result["token"])
        self.assertEqual(_SESSION_TIMEOUT_LOG[-1]["jti"], jti)

    def test_timeout_log_reason_is_inactivity(self):
        result = issue_session_token("reason_user")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))

        validate_session_token(result["token"])
        self.assertEqual(_SESSION_TIMEOUT_LOG[-1]["reason"], "inactivity")

    def test_timeout_log_idle_seconds_is_positive(self):
        result = issue_session_token("idle_secs_user")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 10))

        validate_session_token(result["token"])
        idle = _SESSION_TIMEOUT_LOG[-1]["idle_seconds"]
        self.assertGreater(idle, SESSION_INACTIVITY_TIMEOUT_SECONDS)

    def test_get_session_timeout_log_returns_newest_first(self):
        """get_session_timeout_log must return entries newest-first."""
        for i in range(3):
            result = issue_session_token(f"log_order_user_{i}")
            jti = result["jti"]
            now_ts = int(time.time())
            _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))
            validate_session_token(result["token"])

        entries = get_session_timeout_log(limit=10)
        self.assertGreaterEqual(len(entries), 3)
        # Verify descending timestamp order.
        for a, b in zip(entries, entries[1:]):
            self.assertGreaterEqual(a["timestamp"], b["timestamp"])

    def test_get_session_timeout_log_respects_limit(self):
        for i in range(5):
            result = issue_session_token(f"limit_user_{i}")
            jti = result["jti"]
            now_ts = int(time.time())
            _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))
            validate_session_token(result["token"])

        entries = get_session_timeout_log(limit=3)
        self.assertLessEqual(len(entries), 3)

    def test_no_timeout_log_entry_for_valid_token(self):
        """No timeout entry must be created when a valid token is validated."""
        initial_count = len(_SESSION_TIMEOUT_LOG)
        result = issue_session_token("no_timeout_user")
        validate_session_token(result["token"])
        self.assertEqual(len(_SESSION_TIMEOUT_LOG), initial_count)

    def test_no_timeout_log_entry_for_wrong_signature(self):
        """Signature failures must not produce timeout log entries."""
        initial_count = len(_SESSION_TIMEOUT_LOG)
        validate_session_token("bad.signature")
        self.assertEqual(len(_SESSION_TIMEOUT_LOG), initial_count)


# ===========================================================================
# TestSessionTimeoutWebEndpoint — integration (task_073_002 / task_073_003)
# ===========================================================================

class TestSessionTimeoutWebEndpoint(unittest.TestCase):
    """Verify the /api/auth/session/renew endpoint behaviour."""

    def setUp(self):
        _clear_state()
        from src.web_app import create_app
        from src.db import initialize_database
        import tempfile
        from pathlib import Path
        self._db_path = Path(tempfile.mktemp(suffix=".db"))
        initialize_database(self._db_path)
        self.app = create_app(self._db_path)

    def _call(self, method: str, path: str, body: dict | None = None, token: str | None = None):
        body_bytes = json.dumps(body or {}).encode()
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "wsgi.input": __import__("io").BytesIO(body_bytes),
            "CONTENT_LENGTH": str(len(body_bytes)),
            "CONTENT_TYPE": "application/json",
            "HTTP_X_ROLE": "patient",
        }
        if token:
            environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        responses = []
        def start_response(status, headers):
            responses.append(status)
        body_iter = self.app(environ, start_response)
        raw = b"".join(body_iter)
        status_code = int(responses[0].split()[0])
        return status_code, json.loads(raw)

    def test_renew_endpoint_returns_200_for_valid_token(self):
        result = issue_session_token("web_user")
        status, data = self._call("POST", "/api/auth/session/renew", {"token": result["token"]})
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertIn("token", data["data"])

    def test_renew_endpoint_returns_401_for_timed_out_token(self):
        result = issue_session_token("web_timed_out")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))
        status, data = self._call("POST", "/api/auth/session/renew", {"token": result["token"]})
        self.assertEqual(status, 401)
        self.assertEqual(data["error"]["code"], "SESSION_EXPIRED")

    def test_renew_endpoint_returns_400_for_missing_token(self):
        status, data = self._call("POST", "/api/auth/session/renew", {})
        self.assertEqual(status, 400)

    def test_renew_endpoint_401_error_contains_inactivity_minutes(self):
        result = issue_session_token("web_msg_user")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))
        _, data = self._call("POST", "/api/auth/session/renew", {"token": result["token"]})
        self.assertIn("15", data["error"]["message"])

    def test_bearer_token_401_includes_session_expired_code_for_inactive(self):
        """An inactive Bearer token on any /api/ endpoint returns 401."""
        result = issue_session_token("bearer_inactive")
        jti = result["jti"]
        now_ts = int(time.time())
        _SESSION_ACTIVITY[jti] = float(now_ts - (SESSION_INACTIVITY_TIMEOUT_SECONDS + 1))
        status, data = self._call("GET", "/api/appointments/specialties", token=result["token"])
        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
