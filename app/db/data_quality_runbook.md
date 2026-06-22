# Data Quality Validation Runbook

## Purpose

This runbook covers automated data quality scans, publish gating, quarantine handling, and reporting for critical clinical domains.

## Execution Modes

- `scan`: Run database-backed validation for a single domain.
- `publish-gate`: Validate a publish batch and block severe failures.
- `report`: Export a trend report for a prior quality run.
- `rules`: Print the seeded rule catalog.

## Scheduled Validation

- Run scheduled validations for appointments, patient profiles, reservations, booking events, confirmation deliveries, and reminder logs.
- Run domain-specific scans before pipeline publish stages.
- Keep scheduled runs in observe mode until the rule pack is tuned.

## Publish Gate

- Use block mode for severe failure thresholds on clinical and booking domains.
- Route severe violations to quarantine for triage.
- Do not publish downstream records until the blocking violations are resolved or explicitly waived.

## Alert Routing

- Critical violations route to the owning team with a 15 minute triage SLA.
- Warning violations route to the owning team with a 60 minute triage SLA.
- Observe mode records violations without blocking publish.

## Quarantine Handling

- Quarantine contains records that failed severe validations.
- Triage notes should identify the rule code, domain, and remediation.
- Re-run the same validation scope after remediation to confirm resolution.

## Trend Reporting

- Export the trend report after each run that matters for stakeholder review.
- Review failure counts, blocked counts, and MTTR on a weekly basis.
- Use the report to tune rules and reduce false positives.
