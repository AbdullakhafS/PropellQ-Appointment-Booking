from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import Any
from unittest import TestCase

sys.path.insert(0, ".")

from src.tls_middleware import (
    TLSConfig,
    TLSEnforcementMiddleware,
    TLSPostureValidator,
    TLSCertificateMonitor,
    CertificateInfo,
    WEAK_PROTOCOL_VERSIONS,
    WEAK_CIPHER_PATTERNS,
    STRONG_CIPHERS_TLS12,
    _harden_cookie_value,
)


# ---------------------------------------------------------------------------
# WSGI test helpers
# ---------------------------------------------------------------------------

def _make_environ(
    scheme: str = "http",
    path: str = "/api/test",
    host: str = "example.com",
    forwarded_proto: str | None = None,
    https_header: str | None = None,
) -> dict[str, Any]:
    env: dict[str, Any] = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "HTTP_HOST": host,
        "wsgi.url_scheme": scheme,
        "wsgi.input": BytesIO(b""),
        "wsgi.errors": BytesIO(),
    }
    if forwarded_proto is not None:
        env["HTTP_X_FORWARDED_PROTO"] = forwarded_proto
    if https_header is not None:
        env["HTTPS"] = https_header
    return env


def _dummy_inner_app(environ: dict, start_response):
    body = b'{"ok": true}'
    start_response("200 OK", [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
    ])
    return [body]


def _dummy_app_with_cookie(environ: dict, start_response):
    body = b'{"ok": true}'
    start_response("200 OK", [
        ("Content-Type", "application/json"),
        ("Set-Cookie", "session=abc123; Path=/"),
    ])
    return [body]


class CapturingStartResponse:
    """Records status and headers from start_response calls."""

    def __init__(self) -> None:
        self.status: str = ""
        self.headers: list[tuple[str, str]] = []

    def __call__(
        self,
        status: str,
        headers: list[tuple[str, str]],
        exc_info: Any = None,
    ) -> None:
        self.status = status
        self.headers = headers

    def header(self, name: str) -> str | None:
        name_lower = name.lower()
        for k, v in self.headers:
            if k.lower() == name_lower:
                return v
        return None

    def all_headers(self, name: str) -> list[str]:
        name_lower = name.lower()
        return [v for k, v in self.headers if k.lower() == name_lower]


# ===========================================================================
# Task 001 — TLS Enforcement Architecture
# ===========================================================================

class TestTLSArchitecture(TestCase):
    """AC: TLS termination point documented.
    AC: HTTP-to-HTTPS behavior specified.
    AC: Weak protocols and ciphers identified for disablement."""

    def test_weak_protocols_are_defined(self) -> None:
        """SSLv2, SSLv3, TLS 1.0, TLS 1.1 must be in the disabled set."""
        self.assertIn("SSLv2", WEAK_PROTOCOL_VERSIONS)
        self.assertIn("SSLv3", WEAK_PROTOCOL_VERSIONS)
        self.assertIn("TLSv1.0", WEAK_PROTOCOL_VERSIONS)
        self.assertIn("TLSv1.1", WEAK_PROTOCOL_VERSIONS)

    def test_tls12_and_tls13_not_in_weak_protocols(self) -> None:
        """TLS 1.2 and 1.3 must NOT be disabled."""
        self.assertNotIn("TLSv1.2", WEAK_PROTOCOL_VERSIONS)
        self.assertNotIn("TLSv1.3", WEAK_PROTOCOL_VERSIONS)

    def test_weak_cipher_patterns_cover_known_weaknesses(self) -> None:
        """NULL, EXPORT, RC4, DES, MD5 patterns must be in the weak cipher set."""
        for pattern in ("NULL", "EXPORT", "RC4", "DES", "MD5"):
            self.assertIn(pattern, WEAK_CIPHER_PATTERNS)

    def test_strong_cipher_string_uses_ecdhe_gcm(self) -> None:
        """Strong cipher string must use ECDHE and AES-GCM."""
        self.assertIn("ECDHE", STRONG_CIPHERS_TLS12)
        self.assertIn("GCM", STRONG_CIPHERS_TLS12)

    def test_tls_config_minimum_version_is_tls12(self) -> None:
        config = TLSConfig()
        self.assertEqual(config.min_tls_version, "TLSv1.2")

    def test_tls_config_hsts_header_includes_required_directives(self) -> None:
        config = TLSConfig()
        hsts = config.hsts_header_value
        self.assertIn("max-age=", hsts)
        self.assertIn("includeSubDomains", hsts)

    def test_audit_report_documents_termination_point(self) -> None:
        validator = TLSPostureValidator()
        report = validator.generate_tls_audit_report()
        arch = report["tls_architecture"]
        self.assertIn("TLSEnforcementMiddleware", arch["termination_point"])
        self.assertIn("TLS 1.2", arch["minimum_protocol_version"])
        self.assertIn("disabled_protocols", arch)
        self.assertIn("http_to_https_behavior", arch)


# ===========================================================================
# Task 002 — TLS 1.2+ Configuration and Secure Headers
# ===========================================================================

class TestTLSEnforcementMiddleware(TestCase):
    """AC: HTTP requests redirect or reject as configured.
    AC: TLS 1.2+ is the minimum negotiated version.
    AC: HSTS and secure cookie settings are enabled."""

    # --- HTTP detection ---

    def test_https_request_passes_through(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_inner_app)
        env = _make_environ(scheme="https")
        sr = CapturingStartResponse()
        result = mw(env, sr)
        self.assertEqual(sr.status, "200 OK")

    def test_x_forwarded_proto_https_passes(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_inner_app)
        env = _make_environ(scheme="http", forwarded_proto="https")
        sr = CapturingStartResponse()
        mw(env, sr)
        self.assertEqual(sr.status, "200 OK")

    def test_https_environ_header_passes(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_inner_app)
        env = _make_environ(scheme="http", https_header="on")
        sr = CapturingStartResponse()
        mw(env, sr)
        self.assertEqual(sr.status, "200 OK")

    # --- HTTP redirect ---

    def test_http_request_redirects_to_https_by_default(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_inner_app, TLSConfig(redirect_http=True))
        env = _make_environ(scheme="http", path="/api/appointments")
        sr = CapturingStartResponse()
        mw(env, sr)
        self.assertEqual(sr.status, "301 Moved Permanently")

    def test_http_redirect_location_uses_https_scheme(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_inner_app, TLSConfig(redirect_http=True))
        env = _make_environ(scheme="http", path="/api/search", host="app.example.com")
        sr = CapturingStartResponse()
        mw(env, sr)
        location = sr.header("Location")
        self.assertIsNotNone(location)
        self.assertTrue(location.startswith("https://"))
        self.assertIn("/api/search", location)

    def test_http_redirect_includes_hsts_header(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_inner_app, TLSConfig(redirect_http=True))
        env = _make_environ(scheme="http")
        sr = CapturingStartResponse()
        mw(env, sr)
        hsts = sr.header("Strict-Transport-Security")
        self.assertIsNotNone(hsts)

    def test_http_reject_mode_returns_400(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_inner_app, TLSConfig(redirect_http=False))
        env = _make_environ(scheme="http")
        sr = CapturingStartResponse()
        mw(env, sr)
        self.assertIn("400", sr.status)

    # --- Security headers on HTTPS responses ---

    def test_hsts_header_injected_on_https_response(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_inner_app)
        env = _make_environ(scheme="https")
        sr = CapturingStartResponse()
        mw(env, sr)
        hsts = sr.header("Strict-Transport-Security")
        self.assertIsNotNone(hsts)
        self.assertIn("max-age=", hsts)
        self.assertIn("includeSubDomains", hsts)

    def test_x_content_type_options_injected(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_inner_app)
        env = _make_environ(scheme="https")
        sr = CapturingStartResponse()
        mw(env, sr)
        self.assertEqual(sr.header("X-Content-Type-Options"), "nosniff")

    def test_x_frame_options_injected(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_inner_app)
        env = _make_environ(scheme="https")
        sr = CapturingStartResponse()
        mw(env, sr)
        self.assertEqual(sr.header("X-Frame-Options"), "DENY")

    def test_referrer_policy_injected(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_inner_app)
        env = _make_environ(scheme="https")
        sr = CapturingStartResponse()
        mw(env, sr)
        self.assertIsNotNone(sr.header("Referrer-Policy"))

    # --- Cookie hardening ---

    def test_set_cookie_gets_secure_flag(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_app_with_cookie)
        env = _make_environ(scheme="https")
        sr = CapturingStartResponse()
        mw(env, sr)
        cookie = sr.header("Set-Cookie")
        self.assertIsNotNone(cookie)
        self.assertIn("Secure", cookie)

    def test_set_cookie_gets_httponly_flag(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_app_with_cookie)
        env = _make_environ(scheme="https")
        sr = CapturingStartResponse()
        mw(env, sr)
        cookie = sr.header("Set-Cookie")
        self.assertIn("HttpOnly", cookie)

    def test_set_cookie_gets_samesite_strict(self) -> None:
        mw = TLSEnforcementMiddleware(_dummy_app_with_cookie)
        env = _make_environ(scheme="https")
        sr = CapturingStartResponse()
        mw(env, sr)
        cookie = sr.header("Set-Cookie")
        self.assertIn("SameSite=Strict", cookie)

    def test_harden_cookie_value_idempotent(self) -> None:
        """Hardening a cookie that already has Secure/HttpOnly must not duplicate."""
        already_hardened = "session=abc; Secure; HttpOnly; SameSite=Strict"
        result = _harden_cookie_value(already_hardened)
        self.assertEqual(result.lower().count("secure"), 1)
        self.assertEqual(result.lower().count("httponly"), 1)
        self.assertEqual(result.lower().count("samesite="), 1)


# ===========================================================================
# Task 003 — Certificate Renewal and Monitoring
# ===========================================================================

class TestCertificateLifecycle(TestCase):
    """AC: Certificate renewal automated or operationally defined.
    AC: Expiration monitoring alerts before outages.
    AC: Renewal process documented and testable."""

    def _make_cert_info(self, days_remaining: int) -> CertificateInfo:
        now = datetime.now(tz=timezone.utc)
        return CertificateInfo(
            host="example.com",
            port=443,
            subject={"CN": "example.com"},
            issuer={"O": "Let's Encrypt"},
            serial_number="AABBCC",
            not_before=now - timedelta(days=60),
            not_after=now + timedelta(days=days_remaining),
            tls_version="TLSv1.3",
            cipher_suite="ECDHE-RSA-AES256-GCM-SHA384",
        )

    def test_days_until_expiry_positive(self) -> None:
        cert = self._make_cert_info(90)
        self.assertGreater(cert.days_until_expiry, 0)

    def test_days_until_expiry_near_expiry(self) -> None:
        cert = self._make_cert_info(10)
        self.assertLessEqual(cert.days_until_expiry, 10)

    def test_is_expiring_soon_true_when_below_threshold(self) -> None:
        cert = self._make_cert_info(15)
        self.assertTrue(cert.is_expiring_soon(threshold_days=30))

    def test_is_expiring_soon_false_when_above_threshold(self) -> None:
        cert = self._make_cert_info(60)
        self.assertFalse(cert.is_expiring_soon(threshold_days=30))

    def test_is_expired_false_for_valid_cert(self) -> None:
        cert = self._make_cert_info(5)
        self.assertFalse(cert.is_expired())

    def test_is_expired_true_for_zero_days(self) -> None:
        cert = self._make_cert_info(0)
        self.assertTrue(cert.is_expired())

    def test_certificate_monitor_exists_and_has_expected_interface(self) -> None:
        """TLSCertificateMonitor must expose check_certificate, days_until_expiry,
        and is_expiring_soon methods for operational renewal workflows."""
        monitor = TLSCertificateMonitor()
        self.assertTrue(hasattr(monitor, "check_certificate"))
        self.assertTrue(hasattr(monitor, "days_until_expiry"))
        self.assertTrue(hasattr(monitor, "is_expiring_soon"))

    def test_cert_config_warning_threshold_default(self) -> None:
        config = TLSConfig()
        self.assertEqual(config.cert_expiry_warning_days, 30)

    def test_audit_report_documents_renewal_process(self) -> None:
        cert = self._make_cert_info(45)
        validator = TLSPostureValidator()
        report = validator.generate_tls_audit_report(cert_info=cert)
        self.assertIn("certificate", report)
        self.assertIn("renewal_process", report["certificate"])
        self.assertIn("30", report["certificate"]["renewal_process"])


# ===========================================================================
# Task 004 — TLS Posture Validation and Audit Documentation
# ===========================================================================

class TestTLSPostureAndAudit(TestCase):
    """AC: Security scan confirms TLS 1.2+ posture.
    AC: Audit materials include configuration details and renewal proof."""

    def setUp(self) -> None:
        self.validator = TLSPostureValidator()

    # --- Protocol version validation ---

    def test_tls12_is_valid(self) -> None:
        self.assertTrue(self.validator.validate_tls_version("TLSv1.2"))

    def test_tls13_is_valid(self) -> None:
        self.assertTrue(self.validator.validate_tls_version("TLSv1.3"))

    def test_tls11_is_invalid(self) -> None:
        self.assertFalse(self.validator.validate_tls_version("TLSv1.1"))

    def test_tls10_is_invalid(self) -> None:
        self.assertFalse(self.validator.validate_tls_version("TLSv1.0"))

    def test_sslv3_is_invalid(self) -> None:
        self.assertFalse(self.validator.validate_tls_version("SSLv3"))

    def test_sslv2_is_invalid(self) -> None:
        self.assertFalse(self.validator.validate_tls_version("SSLv2"))

    def test_tls12_normalised_string_valid(self) -> None:
        self.assertTrue(self.validator.validate_tls_version("TLS 1.2"))

    def test_tls13_normalised_string_valid(self) -> None:
        self.assertTrue(self.validator.validate_tls_version("TLS 1.3"))

    # --- Cipher suite validation ---

    def test_ecdhe_aes256_gcm_sha384_is_strong(self) -> None:
        self.assertTrue(
            self.validator.validate_cipher_suite("ECDHE-RSA-AES256-GCM-SHA384")
        )

    def test_rc4_cipher_is_weak(self) -> None:
        self.assertFalse(self.validator.validate_cipher_suite("RC4-MD5"))

    def test_des_cipher_is_weak(self) -> None:
        self.assertFalse(self.validator.validate_cipher_suite("DES-CBC-SHA"))

    def test_export_cipher_is_weak(self) -> None:
        self.assertFalse(self.validator.validate_cipher_suite("EXP-RC4-MD5"))

    def test_null_cipher_is_weak(self) -> None:
        self.assertFalse(self.validator.validate_cipher_suite("NULL-SHA"))

    def test_3des_cipher_is_weak(self) -> None:
        self.assertFalse(self.validator.validate_cipher_suite("DES-CBC3-SHA"))

    def test_get_disabled_protocols_excludes_tls12(self) -> None:
        disabled = self.validator.get_disabled_protocols()
        self.assertNotIn("TLSv1.2", disabled)
        self.assertIn("TLSv1.1", disabled)
        self.assertIn("SSLv3", disabled)

    # --- Audit report structure ---

    def test_audit_report_has_required_fields(self) -> None:
        report = self.validator.generate_tls_audit_report()
        required = [
            "report_type",
            "compliance_standard",
            "generated_at",
            "tls_architecture",
            "tls_12_posture_confirmed",
            "weak_protocols_disabled",
            "weak_cipher_patterns_blocked",
        ]
        for field in required:
            self.assertIn(field, report, f"Missing field: {field}")

    def test_audit_report_references_hipaa_standard(self) -> None:
        report = self.validator.generate_tls_audit_report()
        self.assertIn("HIPAA", report["compliance_standard"])
        self.assertIn("164.312", report["compliance_standard"])

    def test_audit_report_confirms_tls12_posture(self) -> None:
        report = self.validator.generate_tls_audit_report()
        self.assertTrue(report["tls_12_posture_confirmed"])

    def test_audit_report_lists_all_four_weak_protocols(self) -> None:
        report = self.validator.generate_tls_audit_report()
        for proto in ("SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1"):
            self.assertIn(proto, report["weak_protocols_disabled"])

    def test_audit_report_with_cert_info_complete(self) -> None:
        now = datetime.now(tz=timezone.utc)
        cert = CertificateInfo(
            host="api.propeliq.example",
            port=443,
            subject={"CN": "api.propeliq.example"},
            issuer={"O": "Let's Encrypt"},
            serial_number="DEADBEEF",
            not_before=now - timedelta(days=30),
            not_after=now + timedelta(days=60),
            tls_version="TLSv1.3",
            cipher_suite="ECDHE-RSA-AES256-GCM-SHA384",
        )
        report = self.validator.generate_tls_audit_report(cert_info=cert)
        cert_section = report["certificate"]

        self.assertEqual(cert_section["host"], "api.propeliq.example")
        self.assertEqual(cert_section["tls_version"], "TLSv1.3")
        self.assertTrue(cert_section["cipher_is_strong"])
        self.assertFalse(cert_section["is_expired"])
        self.assertIn("renewal_process", cert_section)

    def test_audit_report_hsts_policy_in_architecture(self) -> None:
        report = self.validator.generate_tls_audit_report()
        hsts = report["tls_architecture"]["hsts_policy"]
        self.assertIn("max-age=", hsts)

    def test_audit_report_lists_security_headers(self) -> None:
        report = self.validator.generate_tls_audit_report()
        headers = report["tls_architecture"]["secure_headers"]
        self.assertIn("X-Content-Type-Options", headers)
        self.assertIn("X-Frame-Options", headers)


if __name__ == "__main__":
    import unittest

    unittest.main()
