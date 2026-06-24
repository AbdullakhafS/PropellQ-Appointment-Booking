"""
EP-008 US-089: Async Queue for Reminders — Test Suite

QA-1  Non-Blocking Booking Tests  — enqueue returns immediately
QA-2  Worker Delivery Tests       — workers dispatch reliably
QA-3  Retry / DLQ Tests           — retry logic and dead-letter handling
QA-4  Status Query Tests          — job state is queryable
"""
from __future__ import annotations

import pytest

from src.reminder_queue import (
    MAX_RETRY_COUNT,
    RETRY_BACKOFF_SECONDS,
    AlwaysFailDispatcher,
    DeadLetterEntry,
    FakeDispatcher,
    PartialFailDispatcher,
    QueueStats,
    ReminderChannel,
    ReminderJob,
    ReminderJobStatus,
    ReminderQueue,
    ReminderWorker,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enqueue(
    queue: ReminderQueue,
    appt_id: int = 1,
    patient_id: int = 10,
    channel: ReminderChannel = ReminderChannel.EMAIL,
    window: str = "48h",
    job_id: str | None = None,
) -> tuple[ReminderJob, bool]:
    return queue.enqueue(appt_id, patient_id, channel, window, job_id=job_id)


# ===========================================================================
# QA-1: Non-Blocking Booking Tests (BE-1)
# ===========================================================================


class TestNonBlockingEnqueue:
    """QA-1 — Booking flow enqueues jobs without waiting for dispatch."""

    def test_enqueue_returns_immediately(self):
        q = ReminderQueue()
        job, was_new = _enqueue(q)
        assert was_new is True
        assert isinstance(job, ReminderJob)

    def test_enqueue_sets_status_pending(self):
        q = ReminderQueue()
        job, _ = _enqueue(q)
        assert job.status == ReminderJobStatus.PENDING

    def test_enqueue_assigns_unique_job_id(self):
        q = ReminderQueue()
        j1, _ = _enqueue(q, appt_id=1)
        j2, _ = _enqueue(q, appt_id=2)
        assert j1.job_id != j2.job_id

    def test_idempotent_reenqueue_returns_existing(self):
        q = ReminderQueue()
        job, was_new = _enqueue(q, appt_id=1, channel=ReminderChannel.EMAIL, window="48h")
        _, was_new2 = _enqueue(q, appt_id=1, channel=ReminderChannel.EMAIL, window="48h")
        assert was_new is True
        assert was_new2 is False

    def test_different_channels_are_separate_jobs(self):
        q = ReminderQueue()
        _, n1 = _enqueue(q, channel=ReminderChannel.EMAIL, window="48h")
        _, n2 = _enqueue(q, channel=ReminderChannel.SMS, window="48h")
        assert n1 is True
        assert n2 is True

    def test_different_windows_are_separate_jobs(self):
        q = ReminderQueue()
        _, n1 = _enqueue(q, window="48h")
        _, n2 = _enqueue(q, window="24h")
        _, n3 = _enqueue(q, window="2h")
        assert n1 and n2 and n3

    def test_enqueue_records_appointment_id(self):
        q = ReminderQueue()
        job, _ = _enqueue(q, appt_id=42)
        assert job.appointment_id == 42

    def test_enqueue_records_channel(self):
        q = ReminderQueue()
        job, _ = _enqueue(q, channel=ReminderChannel.SMS)
        assert job.channel == ReminderChannel.SMS

    def test_enqueue_records_reminder_window(self):
        q = ReminderQueue()
        job, _ = _enqueue(q, window="24h")
        assert job.reminder_window == "24h"

    def test_stats_depth_increments_on_enqueue(self):
        q = ReminderQueue()
        _enqueue(q, appt_id=1)
        _enqueue(q, appt_id=2)
        assert q.stats().depth == 2


# ===========================================================================
# QA-2: Worker Delivery Tests (WORKER-1)
# ===========================================================================


class TestWorkerDelivery:
    """QA-2 — Workers dequeue and dispatch reliably."""

    def test_worker_dispatches_pending_job(self):
        q = ReminderQueue()
        dispatcher = FakeDispatcher()
        _enqueue(q)
        worker = ReminderWorker(q, dispatcher)
        worker.process_batch(1)
        assert len(dispatcher.dispatched) == 1

    def test_acked_job_status_is_delivered(self):
        q = ReminderQueue()
        dispatcher = FakeDispatcher()
        job, _ = _enqueue(q)
        worker = ReminderWorker(q, dispatcher)
        worker.process_batch(1)
        assert q.get_job(job.job_id).status == ReminderJobStatus.DELIVERED

    def test_worker_processes_multiple_jobs(self):
        q = ReminderQueue()
        dispatcher = FakeDispatcher()
        for i in range(5):
            _enqueue(q, appt_id=i)
        worker = ReminderWorker(q, dispatcher)
        n = worker.process_batch(10)
        assert n == 5
        assert len(dispatcher.dispatched) == 5

    def test_dequeue_returns_none_on_empty_queue(self):
        q = ReminderQueue()
        assert q.dequeue() is None

    def test_dequeue_changes_status_to_processing(self):
        q = ReminderQueue()
        job, _ = _enqueue(q)
        dequeued = q.dequeue()
        assert dequeued.status == ReminderJobStatus.PROCESSING

    def test_worker_stats_count_successes(self):
        q = ReminderQueue()
        dispatcher = FakeDispatcher()
        _enqueue(q)
        worker = ReminderWorker(q, dispatcher)
        worker.process_batch(1)
        assert worker.worker_stats()["successes"] == 1

    def test_worker_batch_limit_respected(self):
        q = ReminderQueue()
        for i in range(10):
            _enqueue(q, appt_id=i)
        worker = ReminderWorker(q, FakeDispatcher())
        n = worker.process_batch(3)
        assert n == 3

    def test_delivered_job_not_re_queued(self):
        q = ReminderQueue()
        dispatcher = FakeDispatcher()
        _enqueue(q)
        worker = ReminderWorker(q, dispatcher)
        worker.process_batch(1)
        # Re-enqueue same job
        _, was_new = _enqueue(q, appt_id=1, window="48h")
        assert was_new is False


# ===========================================================================
# QA-3: Retry and DLQ Tests (WORKER-2)
# ===========================================================================


class TestRetryAndDeadLetter:
    """QA-3 — Retry logic and dead-letter handling work correctly."""

    def test_nack_increments_retry_count(self):
        q = ReminderQueue()
        job, _ = _enqueue(q)
        q.dequeue()  # move to PROCESSING
        q.nack(job.job_id, "transient error")
        assert q.get_job(job.job_id).retry_count == 1

    def test_nack_below_max_sets_pending_status_for_retry(self):
        q = ReminderQueue()
        job, _ = _enqueue(q)
        q.dequeue()
        q.nack(job.job_id, "err")
        assert q.get_job(job.job_id).status == ReminderJobStatus.PENDING

    def test_nack_at_max_retries_moves_to_dlq(self):
        q = ReminderQueue()
        job, _ = _enqueue(q)
        for _ in range(MAX_RETRY_COUNT):
            q._pending_order.insert(0, job.job_id)
            q._jobs[job.job_id].status = ReminderJobStatus.PENDING
            q.dequeue()
            q.nack(job.job_id, "persistent error")
        assert q.get_job(job.job_id).status == ReminderJobStatus.DEAD_LETTER

    def test_dlq_entry_created_on_exhaustion(self):
        q = ReminderQueue()
        job, _ = _enqueue(q)
        for _ in range(MAX_RETRY_COUNT):
            q._pending_order.insert(0, job.job_id)
            q._jobs[job.job_id].status = ReminderJobStatus.PENDING
            q.dequeue()
            q.nack(job.job_id, "err")
        assert len(q.dead_letters()) == 1

    def test_dlq_entry_has_correct_job_id(self):
        q = ReminderQueue()
        job, _ = _enqueue(q, job_id="test-job-id")
        for _ in range(MAX_RETRY_COUNT):
            q._pending_order.insert(0, job.job_id)
            q._jobs[job.job_id].status = ReminderJobStatus.PENDING
            q.dequeue()
            q.nack(job.job_id, "err")
        assert q.dead_letters()[0].job_id == "test-job-id"

    def test_always_fail_dispatcher_drives_dlq(self):
        q = ReminderQueue()
        dispatcher = AlwaysFailDispatcher()
        _enqueue(q, job_id="fail-job")
        worker = ReminderWorker(q, dispatcher)
        # Process MAX_RETRY_COUNT + 1 times to exhaust retries
        for _ in range(MAX_RETRY_COUNT + 1):
            worker.process_batch(1)
        assert len(q.dead_letters()) == 1

    def test_partial_fail_dispatcher_retries_then_succeeds(self):
        q = ReminderQueue()
        dispatcher = PartialFailDispatcher(fail_count=1)
        job, _ = _enqueue(q)
        worker = ReminderWorker(q, dispatcher)
        worker.process_batch(1)   # fails first attempt
        worker.process_batch(1)   # succeeds on retry
        assert q.get_job(job.job_id).status == ReminderJobStatus.DELIVERED
        assert len(dispatcher.dispatched) == 1

    def test_is_retryable_true_below_max(self):
        job = ReminderJob(
            job_id="j", appointment_id=1, patient_id=1,
            channel=ReminderChannel.EMAIL, reminder_window="48h",
            retry_count=0,
        )
        assert job.is_retryable

    def test_is_retryable_false_at_max(self):
        job = ReminderJob(
            job_id="j", appointment_id=1, patient_id=1,
            channel=ReminderChannel.EMAIL, reminder_window="48h",
            retry_count=MAX_RETRY_COUNT,
        )
        assert not job.is_retryable

    def test_max_retry_count_constant(self):
        assert MAX_RETRY_COUNT == 3

    def test_retry_backoff_has_correct_values(self):
        assert len(RETRY_BACKOFF_SECONDS) == MAX_RETRY_COUNT
        assert RETRY_BACKOFF_SECONDS == [60, 300, 900]

    def test_worker_stats_count_failures(self):
        q = ReminderQueue()
        _enqueue(q)
        worker = ReminderWorker(q, AlwaysFailDispatcher())
        worker.process_batch(1)
        assert worker.worker_stats()["failures"] == 1


# ===========================================================================
# QA-4: Status Query Tests (BE-2 / OPS-1)
# ===========================================================================


class TestStatusQuery:
    """QA-4 — Job state and queue health are queryable."""

    def test_get_job_returns_correct_record(self):
        q = ReminderQueue()
        job, _ = _enqueue(q, job_id="query-job")
        found = q.get_job("query-job")
        assert found is not None
        assert found.job_id == "query-job"

    def test_get_job_returns_none_for_unknown(self):
        assert ReminderQueue().get_job("ghost") is None

    def test_get_jobs_for_appointment_returns_all_channels(self):
        q = ReminderQueue()
        _enqueue(q, appt_id=7, channel=ReminderChannel.EMAIL, window="48h")
        _enqueue(q, appt_id=7, channel=ReminderChannel.SMS, window="48h")
        jobs = q.get_jobs_for_appointment(7)
        assert len(jobs) == 2

    def test_get_jobs_for_appointment_excludes_other_appointments(self):
        q = ReminderQueue()
        _enqueue(q, appt_id=1)
        _enqueue(q, appt_id=2)
        assert len(q.get_jobs_for_appointment(1)) == 1

    def test_stats_returns_queue_stats(self):
        q = ReminderQueue()
        _enqueue(q, appt_id=1)
        _enqueue(q, appt_id=2)
        stats = q.stats()
        assert isinstance(stats, QueueStats)
        assert stats.depth == 2

    def test_stats_delivered_increments_after_ack(self):
        q = ReminderQueue()
        dispatcher = FakeDispatcher()
        _enqueue(q)
        ReminderWorker(q, dispatcher).process_batch(1)
        assert q.stats().delivered == 1

    def test_stats_dlq_count_increments_on_exhaustion(self):
        q = ReminderQueue()
        job, _ = _enqueue(q)
        for _ in range(MAX_RETRY_COUNT):
            q._pending_order.insert(0, job.job_id)
            q._jobs[job.job_id].status = ReminderJobStatus.PENDING
            q.dequeue()
            q.nack(job.job_id, "err")
        assert q.stats().dead_letter_count == 1

    def test_stats_total_enqueued_counts_all(self):
        q = ReminderQueue()
        _enqueue(q, appt_id=1)
        _enqueue(q, appt_id=2)
        assert q.stats().total_enqueued == 2

    def test_stats_worker_failures_accumulated(self):
        q = ReminderQueue()
        _enqueue(q)
        worker = ReminderWorker(q, AlwaysFailDispatcher())
        worker.process_batch(1)
        assert q.stats().worker_failures >= 1

    def test_job_to_dict_has_expected_keys(self):
        q = ReminderQueue()
        job, _ = _enqueue(q)
        d = job.to_dict()
        assert all(k in d for k in ["job_id", "appointment_id", "channel", "status", "retry_count"])

    def test_dead_letter_to_dict_has_expected_keys(self):
        entry = DeadLetterEntry(
            job_id="j", appointment_id=1,
            channel=ReminderChannel.EMAIL, reminder_window="48h",
            retry_count=3,
        )
        d = entry.to_dict()
        assert all(k in d for k in ["job_id", "appointment_id", "channel", "retry_count", "exhausted_at"])
