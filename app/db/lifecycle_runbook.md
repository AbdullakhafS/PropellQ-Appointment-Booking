# Lifecycle Retention and Archive Runbook

## Purpose

This runbook covers the archive and purge lifecycle jobs for regulated datasets. The workflow preserves evidence for compliance review, enforces legal holds, and blocks purge operations inside immutable retention windows.

## Job Schedule

- Archive job: run hourly or daily, depending on backlog size and policy volume.
- Purge job: run after archive processing on the same cadence.
- Report export: run after every successful lifecycle execution.

## Execution Commands

Use the lifecycle CLI from the application root:

```bash
python app/db/lifecycle.py archive --dataset clinical_records --operator scheduler
python app/db/lifecycle.py purge --dataset clinical_records --operator scheduler
python app/db/lifecycle.py report --run-id <run-id>
python app/db/lifecycle.py retrieve --dataset clinical_records --record-key <record-key> --role auditor
```

## Policy Controls

- Archive actions run only for approved policy versions.
- Purge actions skip records under legal hold.
- Purge actions block records that are still inside the immutable retention window.
- Dry-run mode previews eligible records without changing data.

## Alerting And Recovery

- Repeated job failures produce lifecycle alerts with exponential backoff context.
- Terminal failures create a dead-letter event and mark the run failed.
- Use the alert payload to identify the dataset, policy version, and recommended next action.
- If a purge run is blocked by immutable retention, wait for the window to expire and rerun the job.

## Retrieval Verification

- Authorized archive retrieval requires a compliance, auditor, or records-management role.
- Every retrieval updates the archive access count and records an audit event.
- Unauthorized retrieval attempts must be rejected and reviewed.

## Manual Override

- Do not delete archive evidence files during an active investigation.
- If a legal hold is added after archiving, rerun purge in dry-run mode first to confirm the hold is still active.
- If a policy change alters purge timing, record the approved version before the next scheduled run.
