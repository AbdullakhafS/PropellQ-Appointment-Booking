"""
EP-008 US-090: Database Query Optimization with Indexes

DB-1   ``PROPELIQ_INDEX_CATALOG`` — targeted index definitions for the five
       highest-frequency query patterns identified across booking, user,
       queue, and audit workflows.  Each ``IndexDefinition`` carries an
       explicit ``rationale`` and the ``query_patterns`` it accelerates.

DB-2   ``IndexManager.analyze_query_plan()`` uses SQLite's
       ``EXPLAIN QUERY PLAN`` to capture before/after scan types.
       ``QueryPlanResult.uses_index`` distinguishes full-table SCAN from
       index SEARCH, enabling automated plan comparison.

DB-3   ``WriteAmplificationEstimator.estimate()`` calculates the
       amplification ratio as ``proposed_count / existing_count`` so
       write-side impact can be assessed before applying new indexes.
       Any ratio > ``MAX_ACCEPTABLE_WRITE_AMPLIFICATION`` should trigger
       a removal review.

OPS-1  ``PerformanceTelemetry`` records per-query latency samples and
       exposes p50 / p95 / p99 percentiles for baseline/post comparison.
       ``IndexBenchmark`` measures query execution time against a real
       SQLite connection before and after applying each index definition.

Index catalog rationale (DB-1)
-------------------------------
The following query patterns dominate PropelIQ API traffic:

  1. Search available slots by date range
     → SELECT … WHERE status = 'available' AND appointment_date BETWEEN …
  2. Provider-filtered appointment listing (staff queue)
     → SELECT … WHERE provider_id = ? AND status = 'booked'
  3. Checkout / reservation status polling
     → SELECT … WHERE checkout_status = 'reserved' AND reservation_expires_at < ?
  4. Patient appointment history (appointment_id + patient_email)
     → SELECT … WHERE patient_email = ?
  5. Reminder eligibility scan
     → SELECT … WHERE status = 'booked' AND reminder_sent_48h_at IS NULL
  6. Reservation token lookup (unique — already enforced)
     → SELECT … WHERE reservation_token = ?  (appointments table)
  7. Appointment reservation status + expiry cleanup
     → SELECT … WHERE status = 'active' AND expires_at < ?
  8. Patient profile email lookup
     → SELECT … FROM patient_profiles WHERE email = ?
  9. Provider specialty filter (slot search)
     → SELECT … WHERE specialty_id = ? AND is_active = 1
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# OPS-1: Constants
# ---------------------------------------------------------------------------

MAX_ACCEPTABLE_WRITE_AMPLIFICATION: float = 2.0  # flag if ratio > 2×
TELEMETRY_WINDOW_SIZE: int = 1000                 # samples kept per query name


# ---------------------------------------------------------------------------
# DB-1: Index definition
# ---------------------------------------------------------------------------


@dataclass
class IndexDefinition:
    """A single database index with full context for creation and review.

    Attributes
    ----------
    name            Index name (must be unique in the schema).
    table           Table to index.
    columns         Column(s) in index order.
    is_unique       Whether a UNIQUE constraint is implied.
    rationale       Why this index was added (for change review).
    query_patterns  Representative SQL query fragments this index serves.
    """

    name: str
    table: str
    columns: list[str]
    is_unique: bool = False
    rationale: str = ""
    query_patterns: list[str] = field(default_factory=list)

    def create_sql(self) -> str:
        """Return the CREATE INDEX IF NOT EXISTS SQL statement."""
        unique = "UNIQUE " if self.is_unique else ""
        cols = ", ".join(self.columns)
        return (
            f"CREATE {unique}INDEX IF NOT EXISTS {self.name} "
            f"ON {self.table} ({cols})"
        )

    def drop_sql(self) -> str:
        return f"DROP INDEX IF EXISTS {self.name}"


# ---------------------------------------------------------------------------
# DB-1: PropelIQ index catalog
# ---------------------------------------------------------------------------

PROPELIQ_INDEX_CATALOG: list[IndexDefinition] = [
    IndexDefinition(
        name="idx_appointments_status_date",
        table="appointments",
        columns=["status", "appointment_date"],
        rationale=(
            "Accelerates available-slot search queries that filter by status='available' "
            "and a date range.  This is the most frequent query in the booking flow."
        ),
        query_patterns=[
            "SELECT * FROM appointments WHERE status = 'available' AND appointment_date BETWEEN ? AND ?",
            "SELECT * FROM appointments WHERE status = 'available' AND appointment_date >= ?",
        ],
    ),
    IndexDefinition(
        name="idx_appointments_provider_status",
        table="appointments",
        columns=["provider_id", "status"],
        rationale=(
            "Supports staff queue queries that retrieve today's booked appointments "
            "for specific provider IDs.  Eliminates full-table scan for every queue refresh."
        ),
        query_patterns=[
            "SELECT * FROM appointments WHERE provider_id = ? AND status = 'booked'",
            "SELECT * FROM appointments WHERE provider_id IN (…) AND status = 'booked'",
        ],
    ),
    IndexDefinition(
        name="idx_appointments_checkout_expires",
        table="appointments",
        columns=["checkout_status", "reservation_expires_at"],
        rationale=(
            "Speeds up reservation expiry cleanup jobs that scan for "
            "checkout_status='reserved' slots past their expiry window."
        ),
        query_patterns=[
            "SELECT * FROM appointments WHERE checkout_status = 'reserved' AND reservation_expires_at < ?",
        ],
    ),
    IndexDefinition(
        name="idx_appointments_patient_email",
        table="appointments",
        columns=["patient_email"],
        rationale=(
            "Enables fast patient appointment history lookups by email without "
            "scanning the full appointments table."
        ),
        query_patterns=[
            "SELECT * FROM appointments WHERE patient_email = ?",
        ],
    ),
    IndexDefinition(
        name="idx_appointments_reminder_scan",
        table="appointments",
        columns=["status", "reminder_sent_48h_at", "reminder_sent_24h_at", "reminder_sent_2h_at"],
        rationale=(
            "Accelerates reminder eligibility scans that look for booked appointments "
            "where the relevant reminder column is NULL."
        ),
        query_patterns=[
            "SELECT * FROM appointments WHERE status = 'booked' AND reminder_sent_48h_at IS NULL",
            "SELECT * FROM appointments WHERE status = 'booked' AND reminder_sent_24h_at IS NULL",
        ],
    ),
    IndexDefinition(
        name="idx_reservations_status_expires",
        table="appointment_reservations",
        columns=["status", "expires_at"],
        rationale=(
            "Supports reservation cleanup and expiry jobs that query active "
            "reservations approaching or past their expiry time."
        ),
        query_patterns=[
            "SELECT * FROM appointment_reservations WHERE status = 'active' AND expires_at < ?",
        ],
    ),
    IndexDefinition(
        name="idx_patient_profiles_email",
        table="patient_profiles",
        columns=["email"],
        is_unique=True,
        rationale=(
            "Patient lookup by email is required during booking and profile "
            "management.  Unique constraint also enforces data integrity."
        ),
        query_patterns=[
            "SELECT * FROM patient_profiles WHERE email = ?",
        ],
    ),
    IndexDefinition(
        name="idx_providers_specialty_active",
        table="providers",
        columns=["specialty_id", "is_active"],
        rationale=(
            "Supports specialty-filtered provider listing queries used in the "
            "slot-search flow."
        ),
        query_patterns=[
            "SELECT * FROM providers WHERE specialty_id = ? AND is_active = 1",
        ],
    ),
    IndexDefinition(
        name="idx_reminder_log_appointment",
        table="reminder_log",
        columns=["appointment_id", "reminder_type", "delivery_status"],
        rationale=(
            "Accelerates per-appointment reminder history lookups and "
            "deduplication checks in the reminder dispatch job."
        ),
        query_patterns=[
            "SELECT * FROM reminder_log WHERE appointment_id = ? AND reminder_type = ?",
        ],
    ),
]


# ---------------------------------------------------------------------------
# DB-2: Query plan analysis
# ---------------------------------------------------------------------------


@dataclass
class QueryPlanRow:
    """One row from SQLite's EXPLAIN QUERY PLAN output."""

    order: int
    from_: int
    detail: str

    @property
    def is_scan(self) -> bool:
        """True when this row represents a full-table SCAN."""
        return "SCAN" in self.detail.upper() and "INDEX" not in self.detail.upper()

    @property
    def is_index_search(self) -> bool:
        """True when this row represents an indexed SEARCH."""
        return "SEARCH" in self.detail.upper() or (
            "SCAN" in self.detail.upper() and "INDEX" in self.detail.upper()
        )


@dataclass
class QueryPlanResult:
    """Result of an EXPLAIN QUERY PLAN run.

    Attributes
    ----------
    query        The analysed SQL statement.
    rows         Parsed plan rows from SQLite.
    uses_index   True when at least one row is an index search.
    scan_type    'full_scan', 'index_search', or 'mixed'.
    """

    query: str
    rows: list[QueryPlanRow]
    uses_index: bool
    scan_type: str

    def summary(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "uses_index": self.uses_index,
            "scan_type": self.scan_type,
            "plan_rows": [r.detail for r in self.rows],
        }


# ---------------------------------------------------------------------------
# DB-3: Write amplification estimator
# ---------------------------------------------------------------------------


@dataclass
class WriteAmplificationEstimate:
    """Write-side impact analysis for a proposed index change (DB-3).

    ``amplification_ratio`` = proposed_index_count / existing_index_count.
    A ratio > ``MAX_ACCEPTABLE_WRITE_AMPLIFICATION`` (2.0) suggests the
    table has too many indexes and write performance may suffer.

    Attributes
    ----------
    table                   Table name.
    existing_index_count    Number of indexes before the proposed change.
    proposed_index_count    Number of indexes after adding/removing.
    amplification_ratio     Proposed / existing (1.0 = no change).
    acceptable              True when ratio ≤ MAX_ACCEPTABLE_WRITE_AMPLIFICATION.
    """

    table: str
    existing_index_count: int
    proposed_index_count: int
    amplification_ratio: float
    acceptable: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "existing_index_count": self.existing_index_count,
            "proposed_index_count": self.proposed_index_count,
            "amplification_ratio": round(self.amplification_ratio, 2),
            "acceptable": self.acceptable,
        }


class WriteAmplificationEstimator:
    """Estimates write amplification from adding indexes to a table (DB-3)."""

    def estimate(
        self,
        table: str,
        existing_index_count: int,
        indexes_to_add: int,
    ) -> WriteAmplificationEstimate:
        proposed = existing_index_count + indexes_to_add
        ratio = proposed / existing_index_count if existing_index_count > 0 else float(proposed)
        return WriteAmplificationEstimate(
            table=table,
            existing_index_count=existing_index_count,
            proposed_index_count=proposed,
            amplification_ratio=ratio,
            acceptable=ratio <= MAX_ACCEPTABLE_WRITE_AMPLIFICATION,
        )

    def estimate_catalog(
        self,
        conn: sqlite3.Connection,
    ) -> list[WriteAmplificationEstimate]:
        """Estimate write amplification per table for the full index catalog."""
        from collections import Counter
        proposed_by_table: Counter[str] = Counter(
            idx.table for idx in PROPELIQ_INDEX_CATALOG
        )
        estimates = []
        for table, add_count in proposed_by_table.items():
            existing = self._count_existing_indexes(conn, table)
            estimates.append(self.estimate(table, existing, add_count))
        return estimates

    def _count_existing_indexes(self, conn: sqlite3.Connection, table: str) -> int:
        rows = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name=?",
            (table,),
        ).fetchone()
        return rows[0] if rows else 0


# ---------------------------------------------------------------------------
# OPS-1: Performance telemetry
# ---------------------------------------------------------------------------


@dataclass
class PerformanceSample:
    """A single query latency measurement."""

    query_name: str
    latency_ms: float
    sampled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PerformanceTelemetry:
    """Records per-query latency samples and exposes percentile statistics (OPS-1).

    Maintains a bounded ring-buffer of the last ``TELEMETRY_WINDOW_SIZE``
    samples per query name.

    Usage::

        tel = PerformanceTelemetry()
        tel.record("search_available_slots", 12.5)
        tel.record("search_available_slots", 8.1)
        print(tel.p95("search_available_slots"))
    """

    def __init__(self, window_size: int = TELEMETRY_WINDOW_SIZE) -> None:
        self._window = window_size
        self._samples: dict[str, list[float]] = {}

    def record(self, query_name: str, latency_ms: float) -> None:
        buf = self._samples.setdefault(query_name, [])
        buf.append(latency_ms)
        if len(buf) > self._window:
            del buf[: len(buf) - self._window]

    def _percentile(self, query_name: str, p: float) -> float | None:
        samples = self._samples.get(query_name)
        if not samples:
            return None
        sorted_s = sorted(samples)
        idx = max(0, int(len(sorted_s) * p / 100) - 1)
        return sorted_s[min(idx, len(sorted_s) - 1)]

    def p50(self, query_name: str) -> float | None:
        return self._percentile(query_name, 50)

    def p95(self, query_name: str) -> float | None:
        return self._percentile(query_name, 95)

    def p99(self, query_name: str) -> float | None:
        return self._percentile(query_name, 99)

    def summary(self, query_name: str) -> dict[str, Any]:
        samples = self._samples.get(query_name, [])
        if not samples:
            return {"query_name": query_name, "count": 0}
        return {
            "query_name": query_name,
            "count": len(samples),
            "min_ms": round(min(samples), 3),
            "max_ms": round(max(samples), 3),
            "p50_ms": round(self.p50(query_name) or 0, 3),
            "p95_ms": round(self.p95(query_name) or 0, 3),
            "p99_ms": round(self.p99(query_name) or 0, 3),
        }

    def all_query_names(self) -> list[str]:
        return list(self._samples.keys())


# ---------------------------------------------------------------------------
# DB-2: Index manager
# ---------------------------------------------------------------------------


class IndexManager:
    """Applies, removes, and analyses indexes on a SQLite connection (DB-2).

    Usage::

        conn = sqlite3.connect(":memory:")
        mgr  = IndexManager(conn)
        mgr.apply_catalog()        # apply PROPELIQ_INDEX_CATALOG
        plan = mgr.analyze_query_plan(
            "SELECT * FROM appointments WHERE status = 'available'"
        )
        print(plan.uses_index)     # True after idx_appointments_status_date applied
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create_index(self, defn: IndexDefinition) -> None:
        """Execute the CREATE INDEX IF NOT EXISTS DDL."""
        self._conn.execute(defn.create_sql())
        self._conn.commit()

    def drop_index(self, name: str) -> None:
        """Drop an index by name."""
        self._conn.execute(f"DROP INDEX IF EXISTS {name}")
        self._conn.commit()

    def index_exists(self, name: str) -> bool:
        """Return True when *name* exists in sqlite_master."""
        row = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
            (name,),
        ).fetchone()
        return row is not None

    def list_indexes(self, table: str | None = None) -> list[dict[str, Any]]:
        """Return all user-created indexes, optionally filtered by table."""
        if table:
            rows = self._conn.execute(
                "SELECT name, tbl_name, sql FROM sqlite_master "
                "WHERE type='index' AND tbl_name=? AND name NOT LIKE 'sqlite_%'",
                (table,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT name, tbl_name, sql FROM sqlite_master "
                "WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        return [{"name": r[0], "table": r[1], "sql": r[2]} for r in rows]

    def analyze_query_plan(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> QueryPlanResult:
        """Run EXPLAIN QUERY PLAN and return a ``QueryPlanResult``."""
        rows_raw = self._conn.execute(
            f"EXPLAIN QUERY PLAN {sql}", params
        ).fetchall()
        plan_rows = [
            QueryPlanRow(order=r[0], from_=r[1], detail=r[3] if len(r) > 3 else r[2])
            for r in rows_raw
        ]
        uses_index = any(r.is_index_search for r in plan_rows)
        has_scan = any(r.is_scan for r in plan_rows)
        if uses_index and not has_scan:
            scan_type = "index_search"
        elif uses_index and has_scan:
            scan_type = "mixed"
        else:
            scan_type = "full_scan"
        return QueryPlanResult(
            query=sql,
            rows=plan_rows,
            uses_index=uses_index,
            scan_type=scan_type,
        )

    def apply_catalog(
        self,
        catalog: list[IndexDefinition] | None = None,
    ) -> list[str]:
        """Apply all indexes in *catalog* (defaults to PROPELIQ_INDEX_CATALOG).

        Returns the list of index names that were created.
        """
        target = catalog if catalog is not None else PROPELIQ_INDEX_CATALOG
        created = []
        for defn in target:
            self.create_index(defn)
            created.append(defn.name)
        return created

    def count_indexes(self, table: str) -> int:
        """Return the number of indexes currently on *table*."""
        return len(self.list_indexes(table))


# ---------------------------------------------------------------------------
# OPS-1: Benchmark helper
# ---------------------------------------------------------------------------


class IndexBenchmark:
    """Measures query latency before and after applying an index (OPS-1).

    Usage::

        bench = IndexBenchmark(conn, telemetry)
        bench.run("search_slots",
                  "SELECT * FROM appointments WHERE status = 'available'",
                  runs=100)
        print(telemetry.p95("search_slots"))
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        telemetry: PerformanceTelemetry,
    ) -> None:
        self._conn = conn
        self._telemetry = telemetry

    def run(
        self,
        query_name: str,
        sql: str,
        params: tuple[Any, ...] = (),
        runs: int = 50,
    ) -> dict[str, Any]:
        """Execute *sql* *runs* times and record latency samples.

        Returns the telemetry summary after all runs.
        """
        for _ in range(runs):
            t0 = time.monotonic()
            self._conn.execute(sql, params).fetchall()
            latency_ms = (time.monotonic() - t0) * 1000.0
            self._telemetry.record(query_name, latency_ms)
        return self._telemetry.summary(query_name)


def apply_all_indexes(conn: sqlite3.Connection) -> list[str]:
    """Convenience function: apply the full PROPELIQ_INDEX_CATALOG to *conn*."""
    return IndexManager(conn).apply_catalog()
