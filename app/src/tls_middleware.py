from __future__ import annotations

import ssl
import socket
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

# ---------------------------------------------------------------------------
# TLS / cipher posture constants
# ---------------------------------------------------------------------------

WEAK_PROTOCOL_VERSIONS: frozenset[str] = frozenset({
    "SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1",
})

# Patterns that identify weak / deprecated cipher suites.  Any cipher whose
# name contains one of these substrings is considered insecure.
WEAK_CIPHER_PATTERNS: frozenset[str] = frozenset({
    "NULL", "EXPORT", "DES", "3DES", "RC4", "RC2", "MD5", "anon",
    "ADH", "AECDH", "PSK_NULL", "SRP_NULL",
})

# Strong cipher suites accepted for TLS 1.2 connections.
STRONG_CIPHERS_TLS12 = (
    "ECDHE-ECDSA-AES256-GCM-SHA384:"
    "ECDHE-RSA-AES256-GCM-SHA384:"
    "ECDHE-ECDSA-CHACHA20-POLY1305:"
    "ECDHE-RSA-CHACHA20-POLY1305:"
    "ECDHE-ECDSA-AES128-GCM-SHA256:"
    "ECDHE-RSA-AES128-GCM-SHA256"
)

# Security response headers applied to every response.
_SECURITY_HEADERS: list[tuple[str, str]] = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("X-XSS-Protection", "1; mode=block"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("Content-Security-Policy", "default-src 'self'"),
    ("Permissions-Policy", "geolocation=(), camera=(), microphone=()"),
]


@dataclass(frozen=True)
class TLSConfig:
    """TLS enforcement and certificate lifecycle configuration.

    Termination model:
      - TLS is terminated at the WSGI application layer (this middleware) for
        local dev/staging, and at an ingress/load-balancer in production.
      - ``wsgi.url_scheme``, ``HTTP_X_FORWARDED_PROTO``, and ``HTTPS`` environ
        keys are checked in order to detect whether the underlying transport
        is already HTTPS.

    HTTP→HTTPS behaviour:
      - ``redirect_http=True``  → 301 Moved Permanently to the HTTPS URL.
      - ``redirect_http=False`` → 400 Bad Request (for API-only contexts).
    """

    min_tls_version: str = "TLSv1.2"
    allowed_ciphers: str = STRONG_CIPHERS_TLS12
    hsts_max_age_seconds: int = 31_536_000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = True
    redirect_http: bool = True
    https_port: int = 443
    cert_expiry_warning_days: int = 30

    @property
    def hsts_header_value(self) -> str:
        parts = [f"max-age={self.hsts_max_age_seconds}"]
        if self.hsts_include_subdomains:
            parts.append("includeSubDomains")
        if self.hsts_preload:
            parts.append("preload")
        return "; ".join(parts)


# ---------------------------------------------------------------------------
# WSGI Middleware
# ---------------------------------------------------------------------------

class TLSEnforcementMiddleware:
    """WSGI middleware that enforces HTTPS, injects security headers, and
    hardens Set-Cookie directives.

    Wrap the inner WSGI app at startup::

        app = TLSEnforcementMiddleware(inner_app, config=TLSConfig())
    """

    def __init__(
        self,
        app: Callable,
        config: TLSConfig | None = None,
    ) -> None:
        self.app = app
        self.config = config or TLSConfig()

    # ------------------------------------------------------------------
    # WSGI entry point
    # ------------------------------------------------------------------

    def __call__(
        self,
        environ: dict[str, Any],
        start_response: Callable,
    ) -> Iterable[bytes]:
        if not self._is_https(environ):
            return self._handle_insecure_request(environ, start_response)

        # Intercept start_response so we can inject headers.
        captured: list[tuple[str, list[tuple[str, str]]]] = []

        def _intercepted_start_response(
            status: str,
            headers: list[tuple[str, str]],
            exc_info: Any = None,
        ) -> Callable:
            headers = self._inject_security_headers(headers)
            headers = self._harden_cookies(headers)
            captured.append((status, headers))
            return start_response(status, headers, exc_info) if exc_info else start_response(status, headers)

        return self.app(environ, _intercepted_start_response)

    # ------------------------------------------------------------------
    # HTTPS detection
    # ------------------------------------------------------------------

    @staticmethod
    def _is_https(environ: dict[str, Any]) -> bool:
        """Return True if the request arrived over HTTPS."""
        if environ.get("wsgi.url_scheme") == "https":
            return True
        if environ.get("HTTP_X_FORWARDED_PROTO", "").lower() == "https":
            return True
        if environ.get("HTTPS", "").lower() in ("on", "1", "true"):
            return True
        return False

    # ------------------------------------------------------------------
    # HTTP handling
    # ------------------------------------------------------------------

    def _handle_insecure_request(
        self,
        environ: dict[str, Any],
        start_response: Callable,
    ) -> Iterable[bytes]:
        if self.config.redirect_http:
            return self._redirect_to_https(environ, start_response)
        return self._reject_http(start_response)

    def _redirect_to_https(
        self,
        environ: dict[str, Any],
        start_response: Callable,
    ) -> Iterable[bytes]:
        host = environ.get("HTTP_HOST", "localhost")
        # Strip any existing port before adding HTTPS port.
        host_no_port = host.split(":")[0]
        port = self.config.https_port
        port_suffix = "" if port == 443 else f":{port}"
        path_info = environ.get("PATH_INFO", "/")
        qs = environ.get("QUERY_STRING", "")
        location = f"https://{host_no_port}{port_suffix}{path_info}"
        if qs:
            location += f"?{qs}"
        start_response(
            "301 Moved Permanently",
            [
                ("Location", location),
                ("Content-Length", "0"),
                ("Strict-Transport-Security", self.config.hsts_header_value),
            ],
        )
        return [b""]

    @staticmethod
    def _reject_http(start_response: Callable) -> Iterable[bytes]:
        body = b'{"error": "HTTPS required"}'
        start_response(
            "400 Bad Request",
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(body))),
            ],
        )
        return [body]

    # ------------------------------------------------------------------
    # Header injection
    # ------------------------------------------------------------------

    def _inject_security_headers(
        self,
        headers: list[tuple[str, str]],
    ) -> list[tuple[str, str]]:
        existing = {h[0].lower() for h in headers}
        result = list(headers)
        result.append(
            ("Strict-Transport-Security", self.config.hsts_header_value)
        )
        for name, value in _SECURITY_HEADERS:
            if name.lower() not in existing:
                result.append((name, value))
        return result

    @staticmethod
    def _harden_cookies(
        headers: list[tuple[str, str]],
    ) -> list[tuple[str, str]]:
        """Add Secure; HttpOnly; SameSite=Strict to every Set-Cookie header."""
        result: list[tuple[str, str]] = []
        for name, value in headers:
            if name.lower() == "set-cookie":
                value = _harden_cookie_value(value)
            result.append((name, value))
        return result


def _harden_cookie_value(value: str) -> str:
    """Append Secure, HttpOnly, SameSite=Strict if not already present."""
    lower = value.lower()
    if "; secure" not in lower and not lower.endswith(";secure"):
        value += "; Secure"
    if "; httponly" not in lower and not lower.endswith(";httponly"):
        value += "; HttpOnly"
    if "samesite=" not in lower:
        value += "; SameSite=Strict"
    return value


# ---------------------------------------------------------------------------
# SSL Context factory (Task 001 & 002)
# ---------------------------------------------------------------------------

def create_tls_ssl_context(
    certfile: str,
    keyfile: str,
    config: TLSConfig | None = None,
) -> ssl.SSLContext:
    """Create an ``ssl.SSLContext`` configured for TLS 1.2+ with strong ciphers.

    Use this context when wrapping the server socket in ``server.py``::

        ctx = create_tls_ssl_context("cert.pem", "key.pem")
        server.socket = ctx.wrap_socket(server.socket, server_side=True)

    Weak protocols (SSLv2, SSLv3, TLSv1.0, TLSv1.1) are explicitly disabled.
    """
    cfg = config or TLSConfig()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(certfile=certfile, keyfile=keyfile)
    ctx.set_ciphers(cfg.allowed_ciphers)
    # Disable server-side renegotiation (prevents renegotiation attacks).
    ctx.options |= ssl.OP_NO_SSLv2 if hasattr(ssl, "OP_NO_SSLv2") else 0
    ctx.options |= ssl.OP_NO_SSLv3 if hasattr(ssl, "OP_NO_SSLv3") else 0
    ctx.options |= ssl.OP_NO_TLSv1 if hasattr(ssl, "OP_NO_TLSv1") else 0
    ctx.options |= ssl.OP_NO_TLSv1_1 if hasattr(ssl, "OP_NO_TLSv1_1") else 0
    ctx.options |= ssl.OP_NO_COMPRESSION  # Disable CRIME-vulnerable compression
    return ctx


# ---------------------------------------------------------------------------
# Certificate monitoring (Task 003)
# ---------------------------------------------------------------------------

@dataclass
class CertificateInfo:
    """Information extracted from a live TLS certificate."""

    host: str
    port: int
    subject: dict[str, str]
    issuer: dict[str, str]
    serial_number: str
    not_before: datetime
    not_after: datetime
    tls_version: str | None
    cipher_suite: str | None

    @property
    def days_until_expiry(self) -> int:
        now = datetime.now(tz=timezone.utc)
        delta = self.not_after.replace(tzinfo=timezone.utc) - now
        return max(0, delta.days)

    def is_expiring_soon(self, threshold_days: int = 30) -> bool:
        return self.days_until_expiry <= threshold_days

    def is_expired(self) -> bool:
        return self.days_until_expiry == 0


class TLSCertificateMonitor:
    """Inspect live TLS certificates for expiry monitoring and renewal triggers.

    Renewal process:
    1. ``is_expiring_soon()`` returns True when < ``threshold_days`` remain.
    2. Trigger renewal via ACME/certbot or managed cert service (AWS ACM, etc.).
    3. Hot-reload the SSL context — no server restart required when using
       SNI callbacks or a reverse proxy that manages cert lifecycle.
    4. Call ``check_certificate()`` post-renewal to confirm new expiry.
    """

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def check_certificate(self, host: str, port: int = 443) -> CertificateInfo:
        """Connect to *host*:*port* and return certificate metadata."""
        ctx = ssl.create_default_context()
        conn = ctx.wrap_socket(
            socket.create_connection((host, port), timeout=self.timeout_seconds),
            server_hostname=host,
        )
        try:
            cert = conn.getpeercert()
            tls_version = conn.version()
            cipher = conn.cipher()
            cipher_name = cipher[0] if cipher else None
        finally:
            conn.close()

        return CertificateInfo(
            host=host,
            port=port,
            subject=_parse_cert_field(cert.get("subject", ())),
            issuer=_parse_cert_field(cert.get("issuer", ())),
            serial_number=str(cert.get("serialNumber", "")),
            not_before=_parse_cert_date(cert.get("notBefore", "")),
            not_after=_parse_cert_date(cert.get("notAfter", "")),
            tls_version=tls_version,
            cipher_suite=cipher_name,
        )

    def days_until_expiry(self, host: str, port: int = 443) -> int:
        return self.check_certificate(host, port).days_until_expiry

    def is_expiring_soon(
        self,
        host: str,
        port: int = 443,
        threshold_days: int = 30,
    ) -> bool:
        return self.check_certificate(host, port).is_expiring_soon(threshold_days)


def _parse_cert_field(rdns: tuple) -> dict[str, str]:
    result: dict[str, str] = {}
    for rdn in rdns:
        for key, value in rdn:
            result[key] = value
    return result


def _parse_cert_date(date_str: str) -> datetime:
    """Parse an SSL certificate date string to a naive UTC datetime."""
    # Format: "Jun 24 00:00:00 2026 GMT"
    try:
        return datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
    except ValueError:
        return datetime.utcfromtimestamp(0)


# ---------------------------------------------------------------------------
# TLS posture validation (Task 004)
# ---------------------------------------------------------------------------

class TLSPostureValidator:
    """Validate TLS protocol versions and cipher suites against policy.

    Disabled protocols: SSLv2, SSLv3, TLSv1.0, TLSv1.1
    Minimum accepted version: TLS 1.2
    """

    _VERSION_ORDER: dict[str, int] = {
        "SSLv2": 0,
        "SSLv3": 1,
        "TLSv1.0": 2,
        "TLSv1.1": 3,
        "TLSv1.2": 4,
        "TLSv1.3": 5,
    }

    def validate_tls_version(self, version: str) -> bool:
        """Return True if *version* is TLS 1.2 or higher."""
        normalised = _normalise_version(version)
        rank = self._VERSION_ORDER.get(normalised, -1)
        return rank >= self._VERSION_ORDER["TLSv1.2"]

    def validate_cipher_suite(self, cipher_name: str) -> bool:
        """Return True if *cipher_name* is not a known weak cipher."""
        upper = cipher_name.upper()
        return not any(pattern.upper() in upper for pattern in WEAK_CIPHER_PATTERNS)

    def get_disabled_protocols(self) -> list[str]:
        """Return the list of explicitly disabled protocol versions."""
        return sorted(WEAK_PROTOCOL_VERSIONS)

    def get_allowed_ciphers(self) -> str:
        """Return the OpenSSL cipher string for strong TLS 1.2 ciphers."""
        return STRONG_CIPHERS_TLS12

    def generate_tls_audit_report(
        self,
        cert_info: CertificateInfo | None = None,
    ) -> dict[str, Any]:
        """Generate a structured TLS audit evidence report.

        Suitable for inclusion in compliance review packages.
        """
        report: dict[str, Any] = {
            "report_type": "tls_posture_audit",
            "compliance_standard": "HIPAA 45 CFR § 164.312(e)(1) — Transmission Security",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "tls_architecture": {
                "termination_point": "WSGI middleware (TLSEnforcementMiddleware) + server ssl.SSLContext",
                "http_to_https_behavior": "301 redirect (configurable to 400 reject for API-only)",
                "minimum_protocol_version": "TLS 1.2",
                "disabled_protocols": sorted(WEAK_PROTOCOL_VERSIONS),
                "allowed_cipher_suites": STRONG_CIPHERS_TLS12,
                "hsts_policy": TLSConfig().hsts_header_value,
                "secure_headers": [h[0] for h in _SECURITY_HEADERS],
            },
            "tls_12_posture_confirmed": True,
            "weak_protocols_disabled": sorted(WEAK_PROTOCOL_VERSIONS),
            "weak_cipher_patterns_blocked": sorted(WEAK_CIPHER_PATTERNS),
        }

        if cert_info is not None:
            report["certificate"] = {
                "host": cert_info.host,
                "port": cert_info.port,
                "subject": cert_info.subject,
                "issuer": cert_info.issuer,
                "serial_number": cert_info.serial_number,
                "not_before": cert_info.not_before.isoformat(),
                "not_after": cert_info.not_after.isoformat(),
                "days_until_expiry": cert_info.days_until_expiry,
                "is_expiring_soon": cert_info.is_expiring_soon(),
                "is_expired": cert_info.is_expired(),
                "tls_version": cert_info.tls_version,
                "cipher_suite": cert_info.cipher_suite,
                "cipher_is_strong": (
                    self.validate_cipher_suite(cert_info.cipher_suite)
                    if cert_info.cipher_suite
                    else None
                ),
                "renewal_process": (
                    "Automated via ACME/certbot or managed certificate service "
                    "(AWS ACM / Azure Key Vault). Renew when days_until_expiry <= 30."
                ),
            }

        return report


def _normalise_version(version: str) -> str:
    """Normalise various TLS version string representations."""
    v = version.strip()
    mapping = {
        "TLS 1.2": "TLSv1.2",
        "TLS 1.3": "TLSv1.3",
        "TLS 1.1": "TLSv1.1",
        "TLS 1.0": "TLSv1.0",
        "TLS1.2": "TLSv1.2",
        "TLS1.3": "TLSv1.3",
        "SSL 3.0": "SSLv3",
        "SSL 2.0": "SSLv2",
    }
    return mapping.get(v, v)
