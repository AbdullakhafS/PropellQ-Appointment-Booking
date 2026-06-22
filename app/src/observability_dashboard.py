"""
Observability Dashboards and Reliability Reporting

Implements DASH-1, DASH-2, REPORT-1:
- DASH-1: Operational reliability dashboard
- DASH-2: Consumer-focused reliability views
- REPORT-1: Weekly SLO and error-budget export
- AC-4: Dashboard shows uptime/latency/errors/top failing endpoints
- AC-5: Weekly SLO/error-budget report is available
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json


@dataclass
class DashboardPanel:
    """
    Dashboard panel definition.
    
    Represents a visualization on the reliability dashboard.
    """
    
    panel_id: str
    title: str
    panel_type: str  # "gauge", "graph", "table", "stat"
    metric_name: str
    description: str = ""
    query: str = ""
    thresholds: Dict[str, float] = field(default_factory=dict)  # e.g., {"warning": 0.95, "critical": 0.90}
    unit: str = ""  # e.g., "%", "ms"


class OperationalDashboard:
    """
    Operational reliability dashboard (DASH-1, AC-4).
    
    Provides SRE-focused views for incident response and monitoring:
    - Service uptime and availability
    - Latency (p95, p99) by service/endpoint
    - Error rate trends
    - Top failing endpoints
    """
    
    def __init__(self, service_name: str = "platform"):
        """Initialize operational dashboard."""
        self.service_name = service_name
        self.panels: List[DashboardPanel] = []
        self._create_standard_panels()
    
    def _create_standard_panels(self) -> None:
        """Create standard operational panels (DASH-1, AC-4)."""
        
        # Panel 1: Platform Uptime (AC-4)
        self.panels.append(DashboardPanel(
            panel_id="uptime_gauge",
            title="Platform Uptime (30d)",
            panel_type="gauge",
            metric_name="availability_30d",
            description="Current month availability percentage",
            thresholds={"critical": 0.99, "warning": 0.999},
            unit="%"
        ))
        
        # Panel 2: Latency p95 (AC-2, AC-4)
        self.panels.append(DashboardPanel(
            panel_id="latency_p95",
            title="API p95 Latency (5m)",
            panel_type="graph",
            metric_name="latency_p95",
            description="95th percentile latency over last 5 minutes",
            thresholds={"warning": 1000, "critical": 2000},
            unit="ms"
        ))
        
        # Panel 3: Error Rate (AC-4)
        self.panels.append(DashboardPanel(
            panel_id="error_rate",
            title="Error Rate Trend (1h)",
            panel_type="graph",
            metric_name="error_rate",
            description="Request error rate percentage",
            thresholds={"warning": 1.0, "critical": 5.0},
            unit="%"
        ))
        
        # Panel 4: Top Failing Endpoints (AC-4)
        self.panels.append(DashboardPanel(
            panel_id="top_failing",
            title="Top Failing Endpoints (1h)",
            panel_type="table",
            metric_name="top_failing_endpoints",
            description="Endpoints with highest error rates",
            unit="%"
        ))
        
        # Panel 5: Request Volume
        self.panels.append(DashboardPanel(
            panel_id="request_volume",
            title="Request Volume (5m)",
            panel_type="graph",
            metric_name="request_rate",
            description="Requests per second",
            unit="rps"
        ))
        
        # Panel 6: Service Health
        self.panels.append(DashboardPanel(
            panel_id="service_health",
            title="Service Health",
            panel_type="table",
            metric_name="service_health",
            description="Health status of each service",
        ))
    
    def to_json(self) -> str:
        """Export dashboard configuration as JSON."""
        panels_data = [{
            "id": p.panel_id,
            "title": p.title,
            "type": p.panel_type,
            "metric": p.metric_name,
            "thresholds": p.thresholds,
            "unit": p.unit
        } for p in self.panels]
        
        return json.dumps({
            "dashboard": f"{self.service_name}_operational",
            "title": f"{self.service_name.title()} Operational Dashboard",
            "panels": panels_data,
            "refresh_interval": "30s"
        }, indent=2)


class ConsumerDashboard:
    """
    Consumer-focused reliability dashboard (DASH-2).
    
    Simplified views for product, leadership, and customer-facing
    reliability review.
    """
    
    def __init__(self, service_name: str = "platform"):
        """Initialize consumer dashboard."""
        self.service_name = service_name
        self.panels: List[DashboardPanel] = []
        self._create_consumer_panels()
    
    def _create_consumer_panels(self) -> None:
        """Create consumer-focused panels (DASH-2)."""
        
        # Panel 1: Overall Health Score
        self.panels.append(DashboardPanel(
            panel_id="health_score",
            title="Overall Health Score",
            panel_type="gauge",
            metric_name="health_score",
            description="Combined uptime, performance, and error metrics (0-100)",
            unit="score"
        ))
        
        # Panel 2: Monthly SLO Attainment
        self.panels.append(DashboardPanel(
            panel_id="slo_attainment",
            title="Monthly SLO Attainment",
            panel_type="gauge",
            metric_name="slo_attainment_percent",
            description="Percentage of SLO targets met this month",
            thresholds={"critical": 95, "warning": 99},
            unit="%"
        ))
        
        # Panel 3: Error Budget Remaining
        self.panels.append(DashboardPanel(
            panel_id="error_budget",
            title="Error Budget Remaining",
            panel_type="gauge",
            metric_name="error_budget_percent",
            description="Percentage of monthly error budget available",
            unit="%"
        ))
        
        # Panel 4: Incidents This Month
        self.panels.append(DashboardPanel(
            panel_id="incident_count",
            title="Incidents This Month",
            panel_type="stat",
            metric_name="incident_count",
            description="Count of SEV incidents",
        ))
    
    def to_json(self) -> str:
        """Export dashboard as JSON."""
        panels_data = [{
            "id": p.panel_id,
            "title": p.title,
            "type": p.panel_type,
            "metric": p.metric_name,
            "thresholds": p.thresholds,
            "unit": p.unit
        } for p in self.panels]
        
        return json.dumps({
            "dashboard": f"{self.service_name}_consumer",
            "title": f"{self.service_name.title()} Reliability",
            "panels": panels_data,
            "refresh_interval": "5m"
        }, indent=2)


@dataclass
class SLOReportEntry:
    """Single SLO entry in reliability report (REPORT-1, AC-5)."""
    
    slo_name: str
    target: float  # e.g., 0.999
    actual: float  # e.g., 0.9985
    compliant: bool
    error_budget_seconds: float
    error_budget_percent: float
    window_days: int


@dataclass
class ReliabilityReport:
    """
    Weekly reliability and SLO report (REPORT-1, AC-5).
    
    Exports SLO attainment, error budget consumption, and incidents
    for leadership and reliability reviews.
    """
    
    report_date: datetime
    report_period_start: datetime
    report_period_end: datetime
    slo_entries: List[SLOReportEntry] = field(default_factory=list)
    total_slos: int = 0
    slos_met: int = 0
    overall_slo_percent: float = 0.0
    incident_count: int = 0
    incident_severity_breakdown: Dict[str, int] = field(default_factory=dict)
    top_error_endpoints: List[tuple] = field(default_factory=list)
    
    def add_slo_entry(self, entry: SLOReportEntry) -> None:
        """Add SLO entry to report."""
        self.slo_entries.append(entry)
        self.total_slos += 1
        if entry.compliant:
            self.slos_met += 1
    
    def calculate_summary(self) -> None:
        """Calculate report summary statistics (AC-5)."""
        if self.total_slos > 0:
            self.overall_slo_percent = (self.slos_met / self.total_slos) * 100
    
    def to_json(self) -> str:
        """Export report as JSON (AC-5)."""
        return json.dumps({
            "report_date": self.report_date.isoformat(),
            "period": {
                "start": self.report_period_start.isoformat(),
                "end": self.report_period_end.isoformat()
            },
            "summary": {
                "total_slos": self.total_slos,
                "slos_met": self.slos_met,
                "overall_slo_percent": self.overall_slo_percent,
                "incident_count": self.incident_count,
                "severity_breakdown": self.incident_severity_breakdown
            },
            "slo_details": [{
                "name": e.slo_name,
                "target": e.target,
                "actual": e.actual,
                "compliant": e.compliant,
                "error_budget_percent": e.error_budget_percent,
                "window_days": e.window_days
            } for e in self.slo_entries],
            "top_error_endpoints": [
                {"endpoint": ep, "error_rate": rate}
                for ep, rate in self.top_error_endpoints
            ]
        }, indent=2)
    
    def to_html(self) -> str:
        """Export report as HTML for email/viewing (AC-5)."""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                .compliant {{ color: green; font-weight: bold; }}
                .non-compliant {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>Weekly Reliability Report</h1>
            <p>Period: {self.report_period_start.date()} to {self.report_period_end.date()}</p>
            
            <h2>Summary</h2>
            <p>Overall SLO Attainment: <strong>{self.overall_slo_percent:.1f}%</strong></p>
            <p>Incidents: {self.incident_count}</p>
            
            <h2>SLO Details</h2>
            <table>
                <tr>
                    <th>SLO</th>
                    <th>Target</th>
                    <th>Actual</th>
                    <th>Status</th>
                    <th>Error Budget %</th>
                </tr>
        """
        
        for entry in self.slo_entries:
            status = '<span class="compliant">✓ Met</span>' if entry.compliant else '<span class="non-compliant">✗ Missed</span>'
            html += f"""
                <tr>
                    <td>{entry.slo_name}</td>
                    <td>{entry.target*100:.2f}%</td>
                    <td>{entry.actual*100:.2f}%</td>
                    <td>{status}</td>
                    <td>{entry.error_budget_percent:.1f}%</td>
                </tr>
            """
        
        html += """
            </table>
            <hr>
            <p><em>Report generated automatically</em></p>
        </body>
        </html>
        """
        
        return html


class ReportGenerator:
    """
    Generates weekly SLO and error-budget reports (REPORT-1, AC-5).
    """
    
    @staticmethod
    def generate_weekly_report(
        slo_compliances: Dict[str, Dict[str, any]],
        incidents: List[Dict[str, Any]],
        top_error_endpoints: List[tuple]
    ) -> ReliabilityReport:
        """
        Generate weekly reliability report (REPORT-1, AC-5).
        
        Args:
            slo_compliances: SLO compliance data
            incidents: List of incidents this week
            top_error_endpoints: Top endpoints by error rate
        
        Returns:
            Populated reliability report
        """
        now = datetime.utcnow()
        week_start = now - timedelta(days=7)
        
        report = ReliabilityReport(
            report_date=now,
            report_period_start=week_start,
            report_period_end=now
        )
        
        # Add SLO entries
        for slo_name, compliance in slo_compliances.items():
            entry = SLOReportEntry(
                slo_name=slo_name,
                target=compliance.get("target", 0),
                actual=compliance.get("actual", 0),
                compliant=compliance.get("compliant", False),
                error_budget_seconds=compliance.get("error_budget_seconds", 0),
                error_budget_percent=(compliance.get("error_budget_seconds", 0) / 604800.0) * 100,
                window_days=7
            )
            report.add_slo_entry(entry)
        
        # Add incident data
        report.incident_count = len(incidents)
        for incident in incidents:
            severity = incident.get("severity", "LOW")
            report.incident_severity_breakdown[severity] = report.incident_severity_breakdown.get(severity, 0) + 1
        
        # Add error endpoints
        report.top_error_endpoints = top_error_endpoints
        
        # Calculate summary
        report.calculate_summary()
        
        return report
