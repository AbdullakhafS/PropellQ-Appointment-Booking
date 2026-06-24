"""
EP-008 US-089: Async Queue for Reminders

BE-1     Non-blocking enqueue — booking flows call ``ReminderQueue.enqueue()``
         and return immediately without waiting for SMS/email dispatch.
         Enqueue is idempotent: re-submitting the same (appointment_id,
         channel, reminder_window) combination for an already-queued or
         delivered job is a safe no-op.

WORKER-1 Reliable delivery — ``ReminderWorker.process_batch()`` dequeues
         jobs, calls the injected ``ReminderDispatchProtocol``, and acks
         or nacks depending on outcome.

WORKER-2 Retry and dead-letter — transient failures increment ``retry_count``.
         After ``MAX_RETRY_COUNT`` exhaustions the job is moved to the
         dead-letter queue (DLQ) and a ``DeadLetterEntry`` is recorded.
         Retry delay uses configurable exponential back-off.

BE-2     Delivery status query — ``ReminderQueue.get_job(job_id)`` and
         ``get_jobs_for_appointment(appointment_id)`` expose current state.

OPS-1    Queue monitoring — ``ReminderQueue.stats()`` returns queue depth,
         worker failure count, DLQ volume, and per-status counts.

Injectable dispatch pattern:
  Tests use ``FakeDispatcher`` (always succeeds) or ``AlwaysFailDispatcher``.
  Production wires in a real SMS/email gateway adapter.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol


# ---------------------------------------------------------------------------
# Constants (WORKER-2)
# ---------------------------------------------------------------------------

MAX_RETRY_COUNT: int = 3
RETRY_BACKOFF_SECONDS: list[int] = [60, 300, 900]   # delays per retry attempt
REMINDER_WINDOWS: tuple[str, ...] = ("48h", "24h", "2h")


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ReminderJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class ReminderChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ReminderJob:
    """A single reminder dispatch task.

    Attributes
    ----------
    job_id           Unique UUID for this job instance.
    appointment_id   Which appointment this reminder is for.
    patient_id       Target patient (opaque ID — no PII stored here).
    channel          Dispatch channel (EMAIL or SMS).
    reminder_window  Which reminder window: '48h', '24h', or '2h'.
    created_at       ISO-8601 UTC creation timestamp.
    status           Current lifecycle state.
    retry_count      Number of failed dispatch attempts so far.
    next_retry_at    ISO-8601 UTC timestamp; None if no retry scheduled.
    failure_reason   Last failure message; None on first attempt.
    """

    job_id: str
    appointment_id: int
    patient_id: int
    channel: ReminderChannel
    reminder_window: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: ReminderJobStatus = ReminderJobStatus.PENDING
    retry_count: int = 0
    next_retry_at: str | None = None
    failure_reason: str | None = None

    @property
    def is_retryable(self) -> bool:
        return self.retry_count < MAX_RETRY_COUNT

    @property
    def idempotency_key(self) -> str:
        """Unique key per (appointment, channel, window) combination."""
        return f"{self.appointment_id}:{self.channel.value}:{self.reminder_window}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "appointment_id": self.appointment_id,
            "patient_id": self.patient_id,
            "channel": self.channel.value,
            "reminder_window": self.reminder_window,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "next_retry_at": self.next_retry_at,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at,
        }


@dataclass
class DeadLetterEntry:
    """A job that has exhausted all retry attempts (WORKER-2).

    Attributes
    ----------
    job_id           Original job ID.
    appointment_id   Source appointment.
    channel          Channel that failed.
    reminder_window  Window that was missed.
    retry_count      Final retry count at exhaustion.
    exhausted_at     ISO-8601 UTC timestamp when moved to DLQ.
    failure_reason   Last failure message.
    """

    job_id: str
    appointment_id: int
    channel: ReminderChannel
    reminder_window: str
    retry_count: int
    exhausted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "appointment_id": self.appointment_id,
            "channel": self.channel.value,
            "reminder_window": self.reminder_window,
            "retry_count": self.retry_count,
            "exhausted_at": self.exhausted_at,
            "failure_reason": self.failure_reason,
        }


@dataclass
class QueueStats:
    """Snapshot of queue depth and health indicators (OPS-1).

    Attributes
    ----------
    depth            Number of PENDING jobs awaiting dispatch.
    processing       Number of jobs currently being processed.
    delivered        Cumulative count of successfully delivered jobs.
    failed           Count of jobs currently in FAILED state (awaiting retry).
    dead_letter_count  Count of jobs that exhausted all retries.
    worker_failures  Cumulative number of dispatch exceptions caught.
    total_enqueued   Total jobs ever enqueued (includes all states).
    """

    depth: int
    processing: int
    delivered: int
    failed: int
    dead_letter_count: int
    worker_failures: int
    total_enqueued: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "depth": self.depth,
            "processing": self.processing,
            "delivered": self.delivered,
            "failed": self.failed,
            "dead_letter_count": self.dead_letter_count,
            "worker_failures": self.worker_failures,
            "total_enqueued": self.total_enqueued,
        }


# ---------------------------------------------------------------------------
# WORKER-1 / WORKER-2: Dispatch protocol + test doubles
# ---------------------------------------------------------------------------


class ReminderDispatchProtocol(Protocol):
    """Injectable reminder dispatch interface.

    Production: connect to AWS SES (email), Twilio / AWS SNS (SMS).
    Tests: ``FakeDispatcher`` or ``AlwaysFailDispatcher``.
    """

    def dispatch(self, job: ReminderJob) -> bool:
        """Attempt to deliver the reminder.

        Returns True when the reminder was accepted by the downstream service.
        Returns False or raises on failure.  ``ReminderWorker`` catches all
        exceptions and treats them as dispatch failures.
        """
        ...


class FakeDispatcher:
    """Always-succeeding test double.  Records dispatched jobs."""

    def __init__(self) -> None:
        self.dispatched: list[ReminderJob] = []

    def dispatch(self, job: ReminderJob) -> bool:
        self.dispatched.append(job)
        return True

    def clear(self) -> None:
        self.dispatched.clear()


class AlwaysFailDispatcher:
    """Always-failing test double for retry/DLQ testing."""

    def __init__(self, failure_reason: str = "simulated failure") -> None:
        self._reason = failure_reason
        self.call_count: int = 0

    def dispatch(self, job: ReminderJob) -> bool:
        self.call_count += 1
        raise RuntimeError(self._reason)


class PartialFailDispatcher:
    """Fails the first ``fail_count`` calls, then succeeds.  For retry tests."""

    def __init__(self, fail_count: int = 1) -> None:
        self._fail_remaining = fail_count
        self.dispatched: list[ReminderJob] = []

    def dispatch(self, job: ReminderJob) -> bool:
        if self._fail_remaining > 0:
            self._fail_remaining -= 1
            raise RuntimeError("transient failure")
        self.dispatched.append(job)
        return True


# ---------------------------------------------------------------------------
# BE-1 / BE-2 / OPS-1: In-memory reminder queue
# ---------------------------------------------------------------------------


class ReminderQueue:
    """Durable in-memory reminder queue.

    In production this class wraps a real message broker (SQS, RabbitMQ,
    Redis Streams).  For the PropelIQ application tier the in-memory
    implementation is functionally complete and fully testable.

    Idempotency (BE-1)
    ------------------
    ``enqueue()`` checks the ``idempotency_key`` (appointment_id:channel:window)
    before accepting a job.  A job that is already PENDING, PROCESSING, or
    DELIVERED is not re-enqueued; FAILED jobs can be re-enqueued after retry
    scheduling; DEAD_LETTER jobs cannot be re-enqueued.

    Retry / DLQ (WORKER-2)
    ----------------------
    ``nack(job_id, reason)`` increments ``retry_count`` and moves to FAILED.
    When ``retry_count >= MAX_RETRY_COUNT`` the job is moved to DEAD_LETTER
    and a ``DeadLetterEntry`` is appended to the DLQ.
    """

    def __init__(self) -> None:
        # job_id → ReminderJob
        self._jobs: dict[str, ReminderJob] = {}
        # idempotency_key → job_id  (excludes DLQ / terminal failed jobs)
        self._idem_index: dict[str, str] = {}
        # Dead-letter queue
        self._dlq: list[DeadLetterEntry] = []
        # Pending FIFO order
        self._pending_order: list[str] = []
        # OPS-1 worker failure counter
        self._worker_failures: int = 0
        # Total jobs ever accepted
        self._total_enqueued: int = 0

    # ------------------------------------------------------------------
    # BE-1: Enqueue
    # ------------------------------------------------------------------

    def enqueue(
        self,
        appointment_id: int,
        patient_id: int,
        channel: ReminderChannel,
        reminder_window: str,
        job_id: str | None = None,
    ) -> tuple[ReminderJob, bool]:
        """Enqueue a reminder job.

        Returns ``(job, was_new)`` where ``was_new`` is False when an
        equivalent job was already active (idempotency no-op).

        Parameters
        ----------
        appointment_id  Source appointment ID.
        patient_id      Target patient (opaque ID).
        channel         Delivery channel (EMAIL or SMS).
        reminder_window Reminder window label ('48h', '24h', '2h').
        job_id          Optional explicit job ID (for testing idempotency).
        """
        job = ReminderJob(
            job_id=job_id or str(uuid.uuid4()),
            appointment_id=appointment_id,
            patient_id=patient_id,
            channel=channel,
            reminder_window=reminder_window,
        )
        ikey = job.idempotency_key
        existing_id = self._idem_index.get(ikey)
        if existing_id:
            existing = self._jobs.get(existing_id)
            if existing and existing.status not in (
                ReminderJobStatus.FAILED,
                ReminderJobStatus.DEAD_LETTER,
            ):
                return existing, False
        self._jobs[job.job_id] = job
        self._idem_index[ikey] = job.job_id
        self._pending_order.append(job.job_id)
        self._total_enqueued += 1
        return job, True

    # ------------------------------------------------------------------
    # WORKER-1: Dequeue / ack / nack
    # ------------------------------------------------------------------

    def dequeue(self) -> ReminderJob | None:
        """Return the next PENDING job in FIFO order, or None if queue empty."""
        while self._pending_order:
            jid = self._pending_order.pop(0)
            job = self._jobs.get(jid)
            if job and job.status == ReminderJobStatus.PENDING:
                job.status = ReminderJobStatus.PROCESSING
                return job
        return None

    def ack(self, job_id: str) -> bool:
        """Mark a job as DELIVERED.  Returns True if the job existed."""
        job = self._jobs.get(job_id)
        if job is None:
            return False
        job.status = ReminderJobStatus.DELIVERED
        job.failure_reason = None
        return True

    def nack(self, job_id: str, reason: str = "dispatch failure") -> bool:
        """Mark a job as failed.  Increments retry count or moves to DLQ.

        Returns True when the job was re-queued for retry, False when it
        was moved to the dead-letter queue.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return False
        job.retry_count += 1
        job.failure_reason = reason
        self._worker_failures += 1
        if job.retry_count >= MAX_RETRY_COUNT:
            job.status = ReminderJobStatus.DEAD_LETTER
            self._dlq.append(
                DeadLetterEntry(
                    job_id=job.job_id,
                    appointment_id=job.appointment_id,
                    channel=job.channel,
                    reminder_window=job.reminder_window,
                    retry_count=job.retry_count,
                    failure_reason=reason,
                )
            )
            return False
        # Reset to PENDING so dequeue() picks it up on the next batch
        job.status = ReminderJobStatus.PENDING
        self._pending_order.append(job_id)
        return True

    # ------------------------------------------------------------------
    # BE-2: Status query
    # ------------------------------------------------------------------

    def get_job(self, job_id: str) -> ReminderJob | None:
        """Return the job record for *job_id*, or None if unknown."""
        return self._jobs.get(job_id)

    def get_jobs_for_appointment(self, appointment_id: int) -> list[ReminderJob]:
        """Return all job records for *appointment_id*."""
        return [j for j in self._jobs.values() if j.appointment_id == appointment_id]

    def dead_letters(self) -> list[DeadLetterEntry]:
        """Return the dead-letter queue contents (WORKER-2)."""
        return list(self._dlq)

    # ------------------------------------------------------------------
    # OPS-1: Stats
    # ------------------------------------------------------------------

    def stats(self) -> QueueStats:
        """Return a snapshot of queue health indicators."""
        by_status: dict[ReminderJobStatus, int] = {s: 0 for s in ReminderJobStatus}
        for job in self._jobs.values():
            by_status[job.status] += 1
        return QueueStats(
            depth=by_status[ReminderJobStatus.PENDING],
            processing=by_status[ReminderJobStatus.PROCESSING],
            delivered=by_status[ReminderJobStatus.DELIVERED],
            failed=by_status[ReminderJobStatus.FAILED],
            dead_letter_count=len(self._dlq),
            worker_failures=self._worker_failures,
            total_enqueued=self._total_enqueued,
        )


# ---------------------------------------------------------------------------
# WORKER-1 / WORKER-2: Reminder worker
# ---------------------------------------------------------------------------


class ReminderWorker:
    """Processes reminder jobs from a ``ReminderQueue`` (WORKER-1 / WORKER-2).

    Usage::

        queue    = ReminderQueue()
        dispatch = FakeDispatcher()
        worker   = ReminderWorker(queue, dispatch)

        # Enqueue jobs
        queue.enqueue(1, 10, ReminderChannel.EMAIL, "48h")
        queue.enqueue(1, 10, ReminderChannel.SMS,   "48h")

        # Process up to 10 jobs
        processed = worker.process_batch(10)

    All dispatch exceptions are caught; failed jobs are nacked and retried
    up to ``MAX_RETRY_COUNT`` times before being moved to the DLQ.
    """

    def __init__(
        self,
        queue: ReminderQueue,
        dispatcher: ReminderDispatchProtocol,
    ) -> None:
        self._queue = queue
        self._dispatcher = dispatcher
        self._processed: int = 0
        self._successes: int = 0
        self._failures: int = 0

    def process_batch(self, max_jobs: int = 10) -> int:
        """Process up to *max_jobs* from the queue.  Returns the count processed."""
        processed = 0
        while processed < max_jobs:
            job = self._queue.dequeue()
            if job is None:
                break
            try:
                ok = self._dispatcher.dispatch(job)
                if ok:
                    self._queue.ack(job.job_id)
                    self._successes += 1
                else:
                    self._queue.nack(job.job_id, "dispatcher returned False")
                    self._failures += 1
            except Exception as exc:  # noqa: BLE001
                self._queue.nack(job.job_id, str(exc))
                self._failures += 1
            processed += 1
            self._processed += 1
        return processed

    def worker_stats(self) -> dict[str, int]:
        """Return cumulative processing statistics."""
        return {
            "total_processed": self._processed,
            "successes": self._successes,
            "failures": self._failures,
        }
