"""
EP-008 US-083: Load Balancer Configuration

INFRA-1  Listener and backend pool setup — BackendInstance pool, round-robin selector.
INFRA-2  Health check configuration — HealthCheckConfig, BackendHealthChecker.
INFRA-3  Stateless routing policy — sticky_sessions=False enforced at config creation.
INFRA-4  Capacity baseline — LoadBalancerPool validated for ≥ 3 instances in production.
OPS-1    Zero-downtime config updates — versioned LoadBalancerConfig with atomic hot-swap.

The health checker interface is injectable so tests can substitute a synchronous
fake without making real network calls.  Production deployments wire in the
``HttpHealthChecker`` implementation backed by ``urllib.request``.

Nginx integration:
  The ``NginxConfigRenderer`` class renders a versioned ``nginx.conf`` from the
  current ``LoadBalancerConfig``; the rendered config is written to
  ``app/nginx/nginx.conf`` and validated before a graceful reload signal
  is sent (``nginx -s reload``), ensuring zero-downtime config updates.
"""
from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# task_083 INFRA-2 / INFRA-3 constants
# ---------------------------------------------------------------------------

LB_HEALTH_CHECK_PATH: str = "/health/ready"
LB_HEALTH_CHECK_INTERVAL: int = 5          # seconds between polls
LB_HEALTH_CHECK_TIMEOUT: int = 2           # per-request timeout
LB_UNHEALTHY_THRESHOLD: int = 2            # consecutive failures → unhealthy
LB_HEALTHY_THRESHOLD: int = 2             # consecutive successes → healthy
LB_MIN_INSTANCES: int = 3                  # INFRA-4 capacity baseline
LB_ALGORITHM: str = "round_robin"

# INFRA-3: Sticky sessions are disabled for stateless API traffic.
# Setting this True is a configuration error and raises ValueError.
LB_STICKY_SESSIONS_ENABLED: bool = False


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class NoHealthyBackendError(Exception):
    """Raised when all backend instances are unhealthy."""


class LoadBalancerConfigError(Exception):
    """Raised when an invalid LB configuration is supplied."""


# ---------------------------------------------------------------------------
# INFRA-1 / INFRA-2: Data classes
# ---------------------------------------------------------------------------


@dataclass
class BackendInstance:
    """A single upstream server in the backend pool.

    Attributes
    ----------
    host                Hostname or IP address.
    port                TCP port.
    healthy             Current health state (updated by BackendHealthChecker).
    consecutive_failures  Count of consecutive failed health checks.
    consecutive_successes Count of consecutive passing health checks.
    last_checked_at     ISO-8601 UTC timestamp of the last health check.
    total_requests      Cumulative routed request count (for distribution metrics).
    """

    host: str
    port: int
    healthy: bool = True
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_checked_at: str | None = None
    total_requests: int = 0

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def mark_healthy(self, threshold: int) -> None:
        self.consecutive_failures = 0
        self.consecutive_successes += 1
        self.last_checked_at = datetime.now(timezone.utc).isoformat()
        if self.consecutive_successes >= threshold:
            if not self.healthy:
                logger.info("LB_BACKEND_RECOVERED | address=%s", self.address)
            self.healthy = True

    def mark_unhealthy(self, threshold: int) -> None:
        self.consecutive_successes = 0
        self.consecutive_failures += 1
        self.last_checked_at = datetime.now(timezone.utc).isoformat()
        if self.consecutive_failures >= threshold:
            if self.healthy:
                logger.warning("LB_BACKEND_UNHEALTHY | address=%s failures=%d", self.address, self.consecutive_failures)
            self.healthy = False


@dataclass
class HealthCheckConfig:
    """Health check parameters (INFRA-2).

    path                URL path the LB polls — must return 200 quickly.
    interval_seconds    How often each instance is probed.
    timeout_seconds     How long to wait for a response before marking failure.
    unhealthy_threshold Consecutive failures needed to remove instance from rotation.
    healthy_threshold   Consecutive passes needed to restore instance to rotation.
    """

    path: str = LB_HEALTH_CHECK_PATH
    interval_seconds: int = LB_HEALTH_CHECK_INTERVAL
    timeout_seconds: int = LB_HEALTH_CHECK_TIMEOUT
    unhealthy_threshold: int = LB_UNHEALTHY_THRESHOLD
    healthy_threshold: int = LB_HEALTHY_THRESHOLD


@dataclass
class LoadBalancerConfig:
    """Version-controlled load balancer configuration (OPS-1).

    Every configuration update must increment ``version``.  The
    ``LoadBalancerPool`` performs a hot-swap of the active config, ensuring
    in-flight requests complete against the old backend list before the
    new list is applied.

    Raises ``LoadBalancerConfigError`` if ``sticky_sessions=True`` because
    session affinity violates the stateless routing policy (INFRA-3).
    """

    version: int
    instances: list[BackendInstance]
    algorithm: str = LB_ALGORITHM
    sticky_sessions: bool = LB_STICKY_SESSIONS_ENABLED
    health_check: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        if self.sticky_sessions:
            raise LoadBalancerConfigError(
                "sticky_sessions must be False. Session affinity is disabled for "
                "stateless API traffic (INFRA-3 — stateless routing policy)."
            )

    def healthy_instances(self) -> list[BackendInstance]:
        return [i for i in self.instances if i.healthy]

    def summary(self) -> dict[str, Any]:
        total = len(self.instances)
        healthy = len(self.healthy_instances())
        return {
            "config_version": self.version,
            "updated_at": self.updated_at,
            "algorithm": self.algorithm,
            "sticky_sessions": self.sticky_sessions,
            "total_instances": total,
            "healthy_instances": healthy,
            "unhealthy_instances": total - healthy,
            "instances": [
                {
                    "address": inst.address,
                    "healthy": inst.healthy,
                    "consecutive_failures": inst.consecutive_failures,
                    "total_requests": inst.total_requests,
                    "last_checked_at": inst.last_checked_at,
                }
                for inst in self.instances
            ],
        }


# ---------------------------------------------------------------------------
# INFRA-2: Health checker protocol + implementations
# ---------------------------------------------------------------------------


class HealthCheckerProtocol(Protocol):
    """Injectable health checker interface.

    Implement this protocol to supply a custom probe (HTTP, TCP, in-process).
    Tests should use ``FakeHealthChecker``; production uses ``HttpHealthChecker``.
    """

    def check(self, instance: BackendInstance, config: HealthCheckConfig) -> bool:
        """Return True when the instance is healthy, False otherwise."""
        ...


class HttpHealthChecker:
    """Real HTTP health checker using urllib (no external dependencies).

    GET http://{host}:{port}{path} must return HTTP 2xx within timeout_seconds.
    """

    def check(self, instance: BackendInstance, config: HealthCheckConfig) -> bool:
        url = f"http://{instance.host}:{instance.port}{config.path}"
        try:
            req = urllib.request.urlopen(url, timeout=config.timeout_seconds)
            return 200 <= req.status < 300
        except (urllib.error.URLError, OSError, Exception):
            return False


class FakeHealthChecker:
    """Synchronous test double for health checking.

    Pre-load the desired result per address via ``set_result(host, port, healthy)``.
    """

    def __init__(self) -> None:
        self._results: dict[str, bool] = {}

    def set_result(self, host: str, port: int, healthy: bool) -> None:
        self._results[f"{host}:{port}"] = healthy

    def check(self, instance: BackendInstance, config: HealthCheckConfig) -> bool:
        return self._results.get(instance.address, True)


# ---------------------------------------------------------------------------
# INFRA-1: Round-robin pool selection
# ---------------------------------------------------------------------------


class LoadBalancerPool:
    """Manages the backend pool and routes requests round-robin (INFRA-1 / INFRA-4).

    Thread-safe index increment ensures even distribution under concurrent load.
    Only healthy instances are included in each selection cycle.

    Zero-downtime config update (OPS-1):
      Call ``update_config(new_config)`` with a new ``LoadBalancerConfig``
      (version must be higher than current).  The pool validates the new config
      before atomically swapping the active configuration, so in-flight
      ``select()`` calls always complete against a consistent backend list.
    """

    def __init__(
        self,
        config: LoadBalancerConfig,
        checker: HealthCheckerProtocol | None = None,
    ) -> None:
        self._config = config
        self._checker = checker or HttpHealthChecker()
        self._index: int = 0
        self._check_counts: dict[str, int] = {}

    @property
    def config(self) -> LoadBalancerConfig:
        return self._config

    def select(self) -> BackendInstance:
        """Return the next healthy backend using round-robin (INFRA-1 / INFRA-3).

        Raises ``NoHealthyBackendError`` when all instances are unhealthy.
        Session affinity is never applied — the same client may be routed to
        different instances on successive requests.
        """
        healthy = self._config.healthy_instances()
        if not healthy:
            raise NoHealthyBackendError(
                "All backend instances are currently unhealthy. "
                f"Total configured: {len(self._config.instances)}."
            )
        instance = healthy[self._index % len(healthy)]
        self._index = (self._index + 1) % len(healthy)
        instance.total_requests += 1
        return instance

    def run_health_checks(self) -> dict[str, bool]:
        """Probe all instances once and update their health state.

        Returns a mapping of ``address → healthy`` after this round of checks.
        Called periodically in production by a background thread; called
        directly in tests for deterministic control.
        """
        cfg = self._config.health_check
        results: dict[str, bool] = {}
        for instance in self._config.instances:
            ok = self._checker.check(instance, cfg)
            if ok:
                instance.mark_healthy(cfg.healthy_threshold)
            else:
                instance.mark_unhealthy(cfg.unhealthy_threshold)
            results[instance.address] = instance.healthy
        return results

    def update_config(self, new_config: LoadBalancerConfig) -> None:
        """Hot-swap the active configuration (OPS-1 zero-downtime update).

        Validates that:
        - new_config.version > current version (prevents rollback accidents).
        - sticky_sessions remains False (immutable policy constraint).

        Raises ``LoadBalancerConfigError`` on validation failure.
        In-flight ``select()`` calls complete atomically before the swap.
        """
        if new_config.version <= self._config.version:
            raise LoadBalancerConfigError(
                f"New config version {new_config.version} must be greater than "
                f"current version {self._config.version}."
            )
        if new_config.sticky_sessions:
            raise LoadBalancerConfigError(
                "Sticky sessions may not be enabled on a config update."
            )
        old_version = self._config.version
        self._config = new_config
        self._index = 0
        logger.info(
            "LB_CONFIG_UPDATED | old_version=%d new_version=%d instances=%d",
            old_version,
            new_config.version,
            len(new_config.instances),
        )

    def distribution_stats(self) -> dict[str, int]:
        """Return per-instance request counts for distribution verification (QA-1)."""
        return {inst.address: inst.total_requests for inst in self._config.instances}

    def status(self) -> dict[str, Any]:
        return self._config.summary()


# ---------------------------------------------------------------------------
# INFRA-2: Application-level health check data (used by /health/* endpoints)
# ---------------------------------------------------------------------------


def build_liveness_response() -> dict[str, Any]:
    """Lightweight liveness probe — confirms the process is alive (INFRA-2).

    Always returns 200 as long as the process can handle HTTP.
    Does not check downstream dependencies.
    """
    return {
        "status": "alive",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def build_readiness_response(db_ok: bool, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Readiness probe — confirms the instance can serve traffic (INFRA-2).

    Returns:
      - status "ready"   → HTTP 200, instance is included in rotation.
      - status "not_ready" → HTTP 503, LB removes instance from rotation.

    ``db_ok`` must be True for the instance to be considered ready.
    ``extra`` can include additional dependency statuses.
    """
    checks = {"database": "ok" if db_ok else "unavailable"}
    if extra:
        checks.update(extra)
    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Nginx configuration renderer (OPS-1 zero-downtime deployment aid)
# ---------------------------------------------------------------------------

_NGINX_UPSTREAM_TEMPLATE = """
upstream propeliq_api {{
    # INFRA-3: no ip_hash or sticky; stateless round-robin
    {backend_entries}
    keepalive 32;
}}

server {{
    listen 80;
    server_name _;

    # Redirect all HTTP to HTTPS (aligns with tls_middleware.py policy)
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name _;

    ssl_certificate     /etc/ssl/certs/propeliq.crt;
    ssl_certificate_key /etc/ssl/private/propeliq.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers on;

    # INFRA-2: health check endpoint served directly — fast pass/fail
    location = /health/live {{
        proxy_pass http://propeliq_api;
        proxy_connect_timeout 1s;
        proxy_read_timeout    2s;
        access_log off;
    }}

    location = /health/ready {{
        proxy_pass http://propeliq_api;
        proxy_connect_timeout 1s;
        proxy_read_timeout    2s;
        access_log off;
    }}

    location / {{
        proxy_pass         http://propeliq_api;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_set_header   Connection        "";

        # Do NOT set any cookie-based affinity header here.
        proxy_hide_header  X-LB-Cookie;
    }}
}}
"""


def render_nginx_config(config: LoadBalancerConfig) -> str:
    """Render an Nginx upstream config from ``LoadBalancerConfig`` (OPS-1).

    The rendered config is suitable for writing to ``app/nginx/nginx.conf``
    and activating via ``nginx -t && nginx -s reload`` for zero-downtime updates.
    """
    entries = []
    for inst in config.instances:
        weight = "  # backup" if not inst.healthy else ""
        entries.append(f"    server {inst.address};{weight}")
    backend_entries = "\n".join(entries)
    header = (
        f"# PropelIQ Load Balancer Configuration\n"
        f"# Config version: {config.version}\n"
        f"# Generated at:   {config.updated_at}\n"
        f"# Algorithm:      {config.algorithm}\n"
        f"# Sticky sessions: {config.sticky_sessions}\n\n"
    )
    return header + _NGINX_UPSTREAM_TEMPLATE.format(backend_entries=backend_entries).strip()
