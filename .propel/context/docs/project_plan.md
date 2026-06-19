# Project Plan: Unified Patient Access & Clinical Intelligence Platform

Document Version: 1.0  
Date: 2026-06-19  
Status: Draft  
Source Inputs: `.propel/context/docs/spec.md`, `.propel/context/docs/design.md`, `.propel/context/docs/epics.md`

---

## 1. Executive Summary

This project plan defines delivery scope, milestones, team structure, AI-adjusted effort and cost baseline, and risk controls for the PropellQ Appointment Booking System. The plan is based on 22 functional requirements, 10 epics, strict HIPAA/security constraints, and a free/open-source deployment model.

Planning objective: deliver a production-ready, compliance-aligned platform that reduces no-shows, accelerates clinical prep, and supports 10,000+ concurrent users with 99.9% uptime.

Target delivery window: 24 weeks (12 two-week sprints), including stabilization and controlled go-live.

---

## 2. Planning Basis and Assumptions

### 2.1 Inputs Used
- Functional scope: 22 FRs from `spec.md`
- Architecture and NFR constraints: `design.md`
- Epic decomposition and initial effort points: `epics.md`

### 2.2 Key Assumptions
- Project start date: 2026-06-22
- Sprint duration: 2 weeks
- Team velocity baseline: 18 story points/sprint in Sprint 1-2, then 20-22 story points/sprint after ramp-up
- 1 story point = 8 engineering hours (per internal agile guideline)
- Compliance hardening, auditability, and performance tuning are included in scope
- External services (Twilio/SendGrid/Calendar APIs) are available in required regions
- Single-clinic deployment for release 1

### 2.3 Constraints
- No paid cloud managed services
- No Kubernetes/serverless deployment
- Self-managed infrastructure and operational ownership

---

## 3. Scope Definition

### 3.1 In Scope (Release 1)
- Patient booking, preferred slot swap, waitlist, reminders, cancel/reschedule
- Staff walk-in booking, queue management, check-in workflows
- Flexible intake (AI-assisted + manual), insurance soft validation
- 360-degree clinical profile with document ingestion and conflict detection
- ICD-10/CPT suggestion and verification workflow
- RBAC, user administration, MFA for staff/admin
- Patient dashboard, operational KPI dashboard
- HIPAA controls, immutable audit logging, retention controls
- Reliability/performance objectives and monitoring baseline

### 3.2 Out of Scope (Release 1)
- Direct EHR pull integrations
- Multi-tenant/multi-clinic architecture
- Paid managed cloud services and advanced serverless architecture

### 3.3 Requirement Coverage
- FR coverage: 22/22 (100%)
- Epic coverage: EP-001 to EP-008, EP-TECH-001, EP-DATA-001

---

## 4. Work Breakdown and Milestones

## 4.1 Phase Plan

| Phase | Sprint Window | Focus | Exit Criteria |
|------|---------------|-------|---------------|
| Phase 0: Mobilization | Sprint 1 | Delivery setup, architecture runway, environments, backlog readiness | Environments ready, CI checks active, refined backlog for 3 sprints |
| Phase 1: Access and Booking Core | Sprint 2-4 | EP-001, EP-005 foundation, part of EP-004 | End-to-end booking live in test env with auth and audit trail |
| Phase 2: Intake and Operations | Sprint 5-6 | EP-002, EP-004 completion | Intake and staff queue workflows stable, integration tests passing |
| Phase 3: Clinical Intelligence | Sprint 7-9 | EP-003, EP-DATA-001 | 360 profile, coding suggestions, conflict detection validated |
| Phase 4: Compliance and Reliability | Sprint 10 | EP-007, EP-008 hardening | Security controls verified, performance targets met in load tests |
| Phase 5: UAT and Go-Live | Sprint 11-12 | UAT, fixes, release readiness, training and rollout | UAT sign-off, release checklist complete, go-live approved |

### 4.2 Milestone Calendar

| Milestone ID | Target Date | Description | Dependency |
|-------------|-------------|-------------|------------|
| M1 | 2026-07-03 | Project mobilization complete | Team staffing, environment access |
| M2 | 2026-08-14 | Booking + RBAC + reminders demo complete | EP-001, EP-005 partial |
| M3 | 2026-09-11 | Intake + staff queue operational in staging | EP-002, EP-004 |
| M4 | 2026-10-23 | Clinical intelligence beta complete | EP-003, EP-DATA-001 |
| M5 | 2026-11-06 | Compliance/performance gate passed | EP-007, EP-008 |
| M6 | 2026-12-04 | Production go-live | UAT and operational readiness |

---

## 5. AI-Adjusted Effort Baseline

### 5.1 Effort Model

Base estimate from epic decomposition:
- Raw epic points: 154 SP
- Raw engineering hours: 154 x 8 = 1,232 hours

Adjustment model:
- Complexity and compliance uplift (security, audit immutability, NFR hardening, integration overhead): +55%
- AI acceleration (code scaffolding, test generation, repetitive implementation): -18%

Adjusted estimate:
- Adjusted points: 154 x 1.55 x 0.82 = 195.7 SP (rounded to 196 SP)
- Adjusted engineering hours: 196 x 8 = 1,568 hours

Delivery buffer:
- Schedule buffer for dependency and UAT variability: 15%
- Buffered effort: 1,803 hours

### 5.2 Sprint Capacity and Duration

- Planned average velocity: 19-20 SP/sprint first 6 sprints, 16-18 SP/sprint in hardening/UAT sprints
- Planned delivery: 12 sprints total
- Functional completion target: by Sprint 10
- Final hardening/UAT/go-live: Sprint 11-12

---

## 6. Team Composition (Auto-Derived)

Team composition is derived from scope profile: high backend complexity, moderate frontend breadth, strict compliance, and meaningful integration/QA load.

| Role | Allocation | Primary Responsibilities |
|------|------------|--------------------------|
| Project Manager | 0.6 FTE | Plan governance, delivery tracking, stakeholder reporting, risk management |
| Product Owner / Clinical SME | 0.5 FTE | Requirement clarification, acceptance decisions, clinical validation |
| Solution Architect / Tech Lead | 1.0 FTE | Architecture integrity, cross-team technical decisions, quality gates |
| Backend Engineers (ASP.NET) | 2.0 FTE | APIs, domain services, auth, audit, integrations, workers |
| Frontend Engineers (React/TS) | 2.0 FTE | Patient/staff/admin portals, accessibility, dashboard UX |
| Data/AI Engineer | 1.0 FTE | document extraction pipeline, coding suggestions, confidence tuning |
| QA Automation Engineer | 1.0 FTE | test strategy, API/UI automation, regression suite, traceability |
| DevOps/SRE Engineer | 0.7 FTE | CI/CD, infra setup, monitoring, backup/recovery, performance tests |
| Security/Compliance Advisor | 0.3 FTE | HIPAA controls, audit verification, security sign-off |

Effective delivery capacity (engineering roles only) is adequate for 196 SP over 12 sprints with buffer.

---

## 7. Cost Baseline (AI-Adjusted)

Currency: USD  
Costing approach: blended rates x role allocation x 24-week window

| Role | Blended Rate (USD/hr) | Estimated Hours | Cost (USD) |
|------|------------------------|-----------------|------------|
| Project Manager | 85 | 576 | 48,960 |
| Product Owner / Clinical SME | 110 | 480 | 52,800 |
| Solution Architect / Tech Lead | 120 | 960 | 115,200 |
| Backend Engineers | 95 | 1,920 | 182,400 |
| Frontend Engineers | 90 | 1,920 | 172,800 |
| Data/AI Engineer | 105 | 960 | 100,800 |
| QA Automation Engineer | 80 | 960 | 76,800 |
| DevOps/SRE Engineer | 100 | 672 | 67,200 |
| Security/Compliance Advisor | 130 | 288 | 37,440 |

Subtotal labor: 854,400  
Tools/integration/test environments (free-tier + operational overhead): 24,000  
Contingency reserve (10%): 87,840  

Total budget baseline: 966,240 USD

Cost note: AI-assisted implementation is already reflected in reduced engineering effort; no separate AI discount is applied to labor rates.

---

## 8. Risk Register

| Risk ID | Risk Description | Probability | Impact | Exposure | Mitigation Strategy | Owner |
|--------|-------------------|-------------|--------|----------|---------------------|-------|
| R-01 | Clinical coding AI quality below target (98% agreement not reached) | Medium | High | High | Human-in-the-loop thresholds, phased tuning, fallback manual coding workflow | Data/AI Engineer |
| R-02 | Integration instability with Twilio/SendGrid/Calendar APIs | Medium | Medium | Medium | Contract tests, retry/circuit breaker policy, sandbox validation before release | Backend Lead |
| R-03 | HIPAA/audit controls fail compliance review late in cycle | Low | Very High | High | Shift-left compliance checks, immutable log verification each sprint, formal gate at Sprint 10 | Security Advisor |
| R-04 | Performance targets missed at scale (10,000 concurrent users) | Medium | High | High | Early load testing from Sprint 4, cache tuning, query profiling, capacity guardrails | DevOps/SRE |
| R-05 | Scope creep from advanced analytics or EHR requests | High | Medium | High | Change control board, defer to post-release backlog, strict release scope baseline | Project Manager |
| R-06 | Underestimated data conflict edge cases in clinical profiles | Medium | High | High | Expand edge-case dataset, add conflict simulation suite, clinician review sessions | QA + Clinical SME |
| R-07 | Team ramp-up delays in first two sprints | Medium | Medium | Medium | Sprint 1 enablement plan, pairing model, architecture runway completed early | Tech Lead |

---

## 9. Governance and Reporting

- Cadence: daily stand-up, weekly milestone review, sprint review/retro every 2 weeks
- Change governance: scope-impact review required for any change affecting timeline or budget
- Quality gates per sprint:
  - Requirement traceability updated
  - Security controls validated for changed components
  - Test coverage progression and regression pass
  - Operational monitoring updated for new services
- Stage gates:
  - Gate A (Sprint 4): Booking + security baseline
  - Gate B (Sprint 8): Clinical intelligence readiness
  - Gate C (Sprint 10): Compliance + performance certification
  - Gate D (Sprint 12): Go-live approval

---

## 10. Sprint Planning Bridge

Recommended initial sprint allocation to transition into `/create-sprint-plan`:

| Sprint | Primary Epics | Sprint Goal |
|-------|----------------|-------------|
| Sprint 1 | EP-TECH-001, EP-005 | Foundation, auth shell, CI/CD, baseline architecture and backlog readiness |
| Sprint 2 | EP-001, EP-005 | Patient booking flow v1 with secured APIs and audit events |
| Sprint 3 | EP-001, EP-004 | Reminder automation, waitlist basics, staff walk-in/check-in workflows |
| Sprint 4 | EP-001, EP-004, EP-007 | Preferred slot swap and booking hardening; Gate A |
| Sprint 5 | EP-002 | AI/manual intake workflows and insurance pre-check |
| Sprint 6 | EP-002, EP-006 | Intake completion optimization and patient dashboard baseline |
| Sprint 7 | EP-003, EP-DATA-001 | Document ingestion, extraction pipeline, profile assembly v1 |
| Sprint 8 | EP-003 | ICD/CPT suggestion and verification workflow |
| Sprint 9 | EP-003, EP-006 | Conflict detection UX, analytics dashboard enrichment; Gate B |
| Sprint 10 | EP-007, EP-008 | Compliance closure, resilience/performance hardening; Gate C |
| Sprint 11 | EP-008 | UAT cycle 1, defect burn-down, production-readiness rehearsals |
| Sprint 12 | EP-008 | UAT cycle 2, release validation, go-live and hypercare handoff |

Dependencies for next workflow (`/create-sprint-plan`):
- Input artifacts ready: `epics.md` (available), `us_*.md` (to be generated), `project_plan.md` (this document)
- Next recommended step: generate user stories by epic before sprint-level assignment

---

## 11. Approval and Sign-Off

| Approval Area | Owner | Status |
|---------------|-------|--------|
| Scope Baseline | Product Owner | Pending |
| Architecture & NFR Baseline | Solution Architect | Pending |
| Budget Baseline | Project Manager | Pending |
| Compliance Approach | Security/Compliance Advisor | Pending |
| Delivery Plan | Engineering Lead | Pending |

---

## 12. Appendix: Traceability Summary

| Planning Element | Source Artifact |
|------------------|-----------------|
| Functional scope and success metrics | `.propel/context/docs/spec.md` |
| Architecture constraints and NFRs | `.propel/context/docs/design.md` |
| Epic decomposition and seed estimate | `.propel/context/docs/epics.md` |

End of document.
