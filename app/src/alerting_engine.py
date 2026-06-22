"""
Alerting Engine and SLO Burn-Rate Alerts

Implements ALERT-1:
- ALERT-1: Burn-rate alerting rules with multi-window support
- AC-3: SLO burn-rate alerts trigger on degradation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(Enum):
    """Alert status."""
    FIRING = "FIRING"
    RESOLVED = "RESOLVED"


@dataclass
class Alert:
    """
    Alert instance (AC-3).
    
    Represents an alert triggered by burn-rate or metric violation.
    """
    
    alert_name: str
    severity: AlertSeverity
    status: AlertStatus
    timestamp: datetime
    slo_name: Optional[str] = None
    metric_name: Optional[str] = None
    metric_value: float = 0.0
    threshold: float = 0.0
    duration_seconds: Optional[int] = None  # How long rule has been violated
    message: str = ""
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class BurnRateWindow:
    """
    Multi-window burn-rate threshold for alerting (ALERT-1, AC-3).
    
    Uses fast (short) and slow (long) windows to reduce false positives.
    Based on Google SRE burn-rate alerts.
    
    Example windows:
    - 2.0x burn rate over 1 hour → warning (0.1% budget consumed)
    - 5.0x burn rate over 30 minutes → critical (0.05% budget consumed)
    - 10.0x burn rate over 5 minutes → critical (0.008% budget consumed)
    """
    
    window_name: str
    duration_seconds: int
    burn_rate_threshold: float
    alert_severity: AlertSeverity


class BurnRateAlertRule:
    """
    Rule for detecting SLO burn-rate violations (ALERT-1, AC-3).
    
    Monitors if error budget is being consumed too quickly.
    """
    
    def __init__(
        self,
        slo_name: str,
        windows: List[BurnRateWindow]
    ):
        """
        Initialize burn-rate alert rule.
        
        Args:
            slo_name: SLO to monitor
            windows: List of burn-rate windows and thresholds
        """
        self.slo_name = slo_name
        self.windows = windows
        self.last_alert_time: Dict[str, datetime] = {}
    
    def evaluate(
        self,
        slo_compliance: Dict[str, any]
    ) -> Optional[Alert]:
        """
        Evaluate if alert should fire (AC-3).
        
        Args:
            slo_compliance: Compliance data with burn_rate
        
        Returns:
            Alert if threshold exceeded, None otherwise
        """
        if not slo_compliance:
            return None
        
        burn_rate = slo_compliance.get("burn_rate", 0.0)
        
        # Check each window
        for window in self.windows:
            if burn_rate >= window.burn_rate_threshold:
                return Alert(
                    alert_name=f"SLO_Burn_Rate_{self.slo_name}",
                    severity=window.alert_severity,
                    status=AlertStatus.FIRING,
                    timestamp=datetime.utcnow(),
                    slo_name=self.slo_name,
                    metric_value=burn_rate,
                    threshold=window.burn_rate_threshold,
                    duration_seconds=window.duration_seconds,
                    message=f"SLO {self.slo_name} burn rate {burn_rate:.1f}x exceeds {window.burn_rate_threshold}x"
                            f" threshold over {window.duration_seconds}s window"
                )
        
        return None


class AlertingEngine:
    """
    Central alerting engine for evaluating rules and dispatching alerts (ALERT-1, AC-3).
    
    Manages alert rules, deduplication, and routing to handlers.
    """
    
    def __init__(self):
        """Initialize alerting engine."""
        self.rules: List[BurnRateAlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Callable[[Alert], None]] = []
    
    def register_rule(self, rule: BurnRateAlertRule) -> None:
        """Register alert rule."""
        self.rules.append(rule)
    
    def register_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        Register alert handler (e.g., log, email, PagerDuty).
        
        Handler is called when alert fires or resolves.
        """
        self.alert_handlers.append(handler)
    
    def evaluate_all(self, slo_compliances: Dict[str, Dict[str, any]]) -> List[Alert]:
        """
        Evaluate all rules against current SLO compliance data (AC-3).
        
        Args:
            slo_compliances: Map of SLO name to compliance data
        
        Returns:
            List of alerts that fired or resolved
        """
        fired_alerts = []
        
        # Evaluate each rule
        for rule in self.rules:
            compliance = slo_compliances.get(rule.slo_name)
            if not compliance:
                continue
            
            alert = rule.evaluate(compliance)
            alert_key = f"{rule.slo_name}_{alert.severity.value}" if alert else None
            
            if alert:
                # Alert firing
                if alert_key not in self.active_alerts:
                    self.active_alerts[alert_key] = alert
                    fired_alerts.append(alert)
                    
                    # Dispatch to handlers
                    for handler in self.alert_handlers:
                        handler(alert)
            else:
                # Alert resolved
                if alert_key in self.active_alerts:
                    resolved = self.active_alerts[alert_key]
                    resolved.status = AlertStatus.RESOLVED
                    fired_alerts.append(resolved)
                    del self.active_alerts[alert_key]
                    
                    # Dispatch to handlers
                    for handler in self.alert_handlers:
                        handler(resolved)
        
        return fired_alerts


def create_standard_burn_rate_alerts(slo_name: str) -> BurnRateAlertRule:
    """
    Create standard multi-window burn-rate alert rule (ALERT-1, AC-3).
    
    Based on Google SRE best practices for false-positive reduction.
    
    Example windows:
    - 2.0x over 1 hour (consume 0.1% budget/hour → alert in 10 hours)
    - 5.0x over 30 minutes (faster degradation → alert sooner)
    - 10.0x over 5 minutes (immediate degradation → alert immediately)
    """
    windows = [
        # Slow burn (gradual degradation over long window)
        BurnRateWindow(
            window_name="slow_burn",
            duration_seconds=3600,  # 1 hour
            burn_rate_threshold=2.0,
            alert_severity=AlertSeverity.WARNING
        ),
        # Medium burn (degradation over 30 minutes)
        BurnRateWindow(
            window_name="medium_burn",
            duration_seconds=1800,  # 30 minutes
            burn_rate_threshold=5.0,
            alert_severity=AlertSeverity.WARNING
        ),
        # Fast burn (rapid degradation)
        BurnRateWindow(
            window_name="fast_burn",
            duration_seconds=300,  # 5 minutes
            burn_rate_threshold=10.0,
            alert_severity=AlertSeverity.CRITICAL
        ),
    ]
    
    return BurnRateAlertRule(slo_name=slo_name, windows=windows)


# Example alert handlers

def log_alert_handler(alert: Alert) -> None:
    """Log alert to stdout/logging system."""
    status_str = "🚨 FIRING" if alert.status == AlertStatus.FIRING else "✅ RESOLVED"
    print(f"{status_str} {alert.severity.value}: {alert.message}")


def email_alert_handler(alert: Alert, recipient: str = "on-call@propellq.com") -> None:
    """Email alert to on-call engineer (mock implementation)."""
    if alert.status == AlertStatus.FIRING:
        print(f"📧 Email alert to {recipient}: {alert.message}")


def pagerduty_alert_handler(alert: Alert) -> None:
    """Route to PagerDuty for critical alerts (mock implementation)."""
    if alert.severity == AlertSeverity.CRITICAL:
        print(f"📟 PagerDuty incident created: {alert.message}")
