# Sprint Plan: PropellQ Appointment Booking System

Document Version: 1.0  
Date: 2026-06-19  
Status: Draft  
Source Inputs: .propel/context/docs/epics.md, .propel/context/tasks/**/us_*.md  
Note: .propel/context/docs/project_plan.md was not available on this branch, so this plan is derived from epic and user-story artifacts.

---

## 1. Configuration

- Sprint duration: 2 weeks
- Planned sprint count: 14
- Total user stories: 108
- Total story points: 504
- Raw team velocity baseline: 40 SP/sprint
- Planning buffer: 10%
- Effective planning velocity: 36 SP/sprint
- Planned average load: 36 SP/sprint

Formula used:
- Effective velocity = Raw velocity x (1 - buffer)
- Effective velocity = 40 x (1 - 0.10) = 36 SP/sprint

---

## 2. Epic Dependency Map

### 2.1 Epic Workload Summary

| Epic | Stories | Story Points |
|------|---------|--------------|
| EP-001 | 10 | 59 |
| EP-002 | 8 | 46 |
| EP-003 | 12 | 60 |
| EP-004 | 12 | 42 |
| EP-005 | 10 | 44 |
| EP-006 | 17 | 57 |
| EP-007 | 13 | 55 |
| EP-008 | 15 | 71 |
| EP-TECH-001 | 6 | 36 |
| EP-DATA-001 | 5 | 34 |
| Total | 108 | 504 |

### 2.2 Dependency Edges (from epics)

- EP-TECH-001 blocks EP-001 through EP-008 delivery velocity
- EP-005 has no upstream dependency (foundation)
- EP-007 has no upstream dependency (foundation)
- EP-001 depends on EP-005, EP-007, EP-008
- EP-002 depends on EP-001, EP-005, EP-007
- EP-003 depends on EP-001, EP-002, EP-005, EP-007, plus external AI integrations
- EP-004 depends on EP-001, EP-005, EP-007, EP-008
- EP-006 depends on EP-001, EP-003, EP-005
- EP-DATA-001 supports EP-003, EP-006, EP-007, EP-008
- EP-008 is cross-cutting and depends on system maturity across all epics

### 2.3 Critical Path

EP-TECH-001 -> EP-005 and EP-007 -> EP-001 -> EP-002 -> EP-003 -> EP-006 -> EP-008

Supporting parallel stream:
EP-DATA-001 begins early and feeds EP-003, EP-006, EP-008 readiness.

---

## 3. Dependency-Ordered Sprint Backlog

## Sprint 1 (34 SP)
Sprint goal: Establish engineering runway and core auth/security baseline.

- EP-TECH-001: US-098, US-099, US-100 (18 SP)
- EP-005: US-043, US-044, US-045 (11 SP)
- EP-007: US-070 (5 SP)

## Sprint 2 (36 SP)
Sprint goal: Complete foundation architecture and expand access controls.

- EP-TECH-001: US-101, US-102, US-103 (18 SP)
- EP-005: US-046, US-047, US-048 (13 SP)
- EP-007: US-071 (5 SP)

## Sprint 3 (36 SP)
Sprint goal: Close foundational identity and compliance controls before product flow work.

- EP-005: US-049, US-050, US-051, US-052 (20 SP)
- EP-007: US-072, US-073, US-074, US-075 (16 SP)

## Sprint 4 (38 SP)
Sprint goal: Start patient booking core and bootstrap data-governance platform.

- EP-001: US-001, US-002, US-004, US-006 (20 SP)
- EP-007: US-076, US-077 (10 SP)
- EP-DATA-001: US-104 (8 SP)

## Sprint 5 (36 SP)
Sprint goal: Complete core booking behavior and booking experience.

- EP-001: US-003, US-005, US-007, US-008, US-010 (31 SP)
- EP-007: US-078 (5 SP)

## Sprint 6 (36 SP)
Sprint goal: Finish booking deep flows and begin intake capability.

- EP-001: US-009 (8 SP)
- EP-002: US-011, US-012, US-014, US-015 (23 SP)
- EP-007: US-079 (5 SP)

## Sprint 7 (36 SP)
Sprint goal: Complete intake scope and begin staff operations features.

- EP-002: US-013, US-016, US-017, US-018 (23 SP)
- EP-004: US-031, US-032, US-033, US-036 (10 SP)
- EP-007: US-080 (3 SP)

## Sprint 8 (38 SP)
Sprint goal: Complete appointment operations and queue management.

- EP-004: US-034, US-035, US-037, US-038, US-039, US-040, US-041, US-042 (32 SP)
- EP-007: US-081, US-082 (6 SP)

## Sprint 9 (38 SP)
Sprint goal: Start clinical intelligence with data-platform enablers.

- EP-DATA-001: US-105, US-106 (13 SP)
- EP-003: US-019, US-020, US-021, US-022 (20 SP)
- EP-006: US-053 (5 SP)

## Sprint 10 (36 SP)
Sprint goal: Continue clinical intelligence and begin patient dashboard work.

- EP-003: US-023, US-024, US-025, US-026, US-027 (25 SP)
- EP-DATA-001: US-107 (5 SP)
- EP-006: US-054, US-055 (6 SP)

## Sprint 11 (37 SP)
Sprint goal: Complete clinical intelligence and advance analytics foundations.

- EP-003: US-028, US-029, US-030 (15 SP)
- EP-DATA-001: US-108 (8 SP)
- EP-006: US-056, US-057, US-058, US-059 (14 SP)

## Sprint 12 (35 SP)
Sprint goal: Complete most portal/reporting scope and open reliability hardening.

- EP-006: US-060, US-061, US-062, US-063, US-064 (17 SP)
- EP-008: US-083, US-084, US-085, US-096 (18 SP)

## Sprint 13 (33 SP)
Sprint goal: Finish portal/reporting scope and continue reliability/performance work.

- EP-006: US-065, US-066, US-067, US-068, US-069 (15 SP)
- EP-008: US-086, US-087, US-088, US-097 (18 SP)

## Sprint 14 (35 SP)
Sprint goal: Complete reliability, scalability, and final production hardening.

- EP-008: US-089, US-090, US-091, US-092, US-093, US-094, US-095 (35 SP)

---

## 4. Sprint Goals Summary

| Sprint | Goal Focus | Planned SP |
|--------|------------|------------|
| 1 | Foundation runway and initial security | 34 |
| 2 | Foundation completion and access controls | 36 |
| 3 | Identity and compliance closure | 36 |
| 4 | Booking start + data foundation | 38 |
| 5 | Booking core completion | 36 |
| 6 | Booking deep flow + intake kickoff | 36 |
| 7 | Intake completion + ops kickoff | 36 |
| 8 | Operations and queue completion | 38 |
| 9 | Clinical intelligence phase 1 | 38 |
| 10 | Clinical intelligence phase 2 | 36 |
| 11 | Clinical intelligence closure | 37 |
| 12 | Portal near-complete + reliability kickoff | 35 |
| 13 | Portal completion + reliability continuation | 33 |
| 14 | Reliability and production hardening | 35 |

---

## 5. Capacity and Load Balance Assessment

### 5.1 Load Distribution

- Min load: 33 SP (Sprint 13)
- Max load: 38 SP (Sprints 4, 8, 9)
- Average load: 36 SP
- Distribution quality: Balanced (within +-3 SP from mean in all sprints)

### 5.2 Risk Flags by Sprint

- Sprints 4, 8, 9 at 38 SP are peak-load windows with integration-heavy stories.
- Sprint 13 at 33 SP intentionally lower to absorb carry-over from reliability work.
- Recommended: maintain 10% explicit contingency inside each sprint board for unplanned technical tasks.

---

## 6. Coverage Report

### 6.1 Epic Coverage

| Epic | Covered in Sprints |
|------|---------------------|
| EP-TECH-001 | 1-2 |
| EP-005 | 1-3 |
| EP-007 | 1-8 |
| EP-001 | 4-6 |
| EP-002 | 6-7 |
| EP-004 | 7-8 |
| EP-DATA-001 | 4, 9-11 |
| EP-003 | 9-11 |
| EP-006 | 9-13 |
| EP-008 | 12-14 |

### 6.2 Story Coverage

- Total planned stories: 108 of 108
- Total planned points: 504 of 504
- Unallocated stories: 0
- Unallocated points: 0

### 6.3 Requirement Coverage Confidence

Given all epic stories are allocated, this sprint plan provides full backlog-to-sprint coverage for FR, NFR/TR, and DR-derived work represented in the current story set.

---

## 7. Execution Notes

- Start each sprint with dependency check against upstream story completion.
- Keep strict entry criteria for EP-003 and EP-008 stories because they are integration-sensitive.
- Track burn-up by epic and not only by sprint to protect critical-path delivery.
- Replan gate recommended after Sprint 6 and Sprint 11.

End of document.
# Sprint Plan: PropellQ Appointment Booking System

Document Version: 1.0  
Date: 2026-06-19  
Status: Draft  
Source Inputs: .propel/context/docs/epics.md, .propel/context/tasks/**/us_*.md  
Output: Dependency-ordered sprint backlog and capacity plan

---

## 1. Configuration

- Sprint duration: 2 weeks
- Planning horizon: 14 sprints
- Delivery model: 2 parallel squads (Platform + Product)
- Raw velocity: 44 SP/sprint (22 SP per squad)
- Risk buffer: 15%
- Effective planning velocity: 37 SP/sprint
- Total user stories: 108
- Total story points: 504
- Required capacity at effective velocity: ~13.6 sprints (rounded to 14)

Note: project_plan.md is not available on this branch; this sprint plan is generated from epics and user stories only.

---

## 2. Epic Dependency Map

| Epic | Depends On | Notes |
|------|------------|-------|
| EP-TECH-001 | None | Technical bootstrap; should start first |
| EP-005 | None | Identity/RBAC foundation |
| EP-007 | None | Compliance baseline; cross-cutting |
| EP-DATA-001 | Supports EP-003/EP-006/EP-007/EP-008 | Start early to reduce downstream blockers |
| EP-001 | EP-005, EP-007, EP-008 (baseline) | Booking core |
| EP-004 | EP-001, EP-005, EP-007, EP-008 | Ops and queue depend on booking core |
| EP-002 | EP-001, EP-005, EP-007 | Intake after booking/auth/compliance baseline |
| EP-003 | EP-002, EP-001, EP-005, EP-007 | Clinical intelligence after intake and platform baseline |
| EP-006 | EP-001, EP-003, EP-005 | Dashboard depends on booking and clinical data |
| EP-008 | All epics (full hardening) | Reliability is cross-cutting and finalized late |

---

## 3. Dependency-Ordered Sprint Backlog

| Sprint | Planned Stories | Epic Coverage | Planned SP |
|--------|------------------|---------------|------------|
| Sprint 1 | US-098, US-099, US-043, US-044, US-045, US-070, US-071, US-104 | EP-TECH-001, EP-005, EP-007, EP-DATA-001 | 39 |
| Sprint 2 | US-100, US-101, US-046, US-047, US-072, US-073, US-074, US-105 | EP-TECH-001, EP-005, EP-007, EP-DATA-001 | 37 |
| Sprint 3 | US-102, US-103, US-048, US-049, US-075, US-076, US-106 | EP-TECH-001, EP-005, EP-007, EP-DATA-001 | 41 |
| Sprint 4 | US-050, US-051, US-052, US-077, US-078, US-107, US-083 | EP-005, EP-007, EP-DATA-001, EP-008 | 35 |
| Sprint 5 | US-001, US-002, US-004, US-006, US-084, US-085, US-031, US-032, US-033 | EP-001, EP-004, EP-008 | 38 |
| Sprint 6 | US-003, US-005, US-007, US-008, US-034, US-037, US-086 | EP-001, EP-004, EP-008 | 40 |
| Sprint 7 | US-009, US-010, US-039, US-040, US-041, US-042, US-087 | EP-001, EP-004, EP-008 | 36 |
| Sprint 8 | US-011, US-012, US-013, US-014, US-035, US-036, US-038, US-088 | EP-002, EP-004, EP-008 | 38 |
| Sprint 9 | US-015, US-016, US-017, US-018, US-089, US-090 | EP-002, EP-008 | 30 |
| Sprint 10 | US-019, US-020, US-021, US-022, US-023, US-024, US-091 | EP-003, EP-008 | 35 |
| Sprint 11 | US-025, US-026, US-027, US-028, US-029, US-030, US-053, US-054 | EP-003, EP-006 | 38 |
| Sprint 12 | US-055, US-056, US-057, US-058, US-059, US-060, US-061, US-079, US-080, US-092 | EP-006, EP-007, EP-008 | 38 |
| Sprint 13 | US-062, US-063, US-064, US-065, US-066, US-081, US-082, US-108 | EP-006, EP-007, EP-DATA-001 | 29 |
| Sprint 14 | US-067, US-068, US-069, US-093, US-094, US-095, US-096, US-097 | EP-006, EP-008 | 30 |

---

## 4. Sprint Goals

| Sprint | Goal |
|--------|------|
| Sprint 1 | Establish technical, security, compliance, and data platform foundations |
| Sprint 2 | Complete baseline auth/compliance controls and engineering standards |
| Sprint 3 | Finalize foundations and unblock feature delivery at scale |
| Sprint 4 | Complete identity/compliance baseline and start reliability instrumentation |
| Sprint 5 | Deliver booking flow v1 plus initial operations workflow |
| Sprint 6 | Deliver booking critical path (slot lock, swap, integration-heavy stories) |
| Sprint 7 | Complete booking/queue feature set with stable operational workflows |
| Sprint 8 | Start intake capabilities and finish remaining queue dependencies |
| Sprint 9 | Complete intake and insurance workflows |
| Sprint 10 | Start clinical intelligence pipeline and 360 profile baseline |
| Sprint 11 | Complete clinical coding flows and expose dashboard baseline |
| Sprint 12 | Expand dashboards and close compliance/reliability gap items |
| Sprint 13 | Complete remaining dashboard and data-governance stories |
| Sprint 14 | Final reliability stories and release-readiness hardening |

---

## 5. Critical Path Analysis

Primary critical path:
1. EP-TECH-001 + EP-005 + EP-007 + EP-DATA-001 foundations (Sprint 1-4)
2. EP-001 booking core (Sprint 5-7)
3. EP-002 intake (Sprint 8-9)
4. EP-003 clinical intelligence (Sprint 10-11)
5. EP-006 dashboard completion + EP-008 final hardening (Sprint 12-14)

Critical-path risks:
- Delay in EP-007 compliance controls impacts all downstream functional acceptance.
- Delay in EP-001 booking delays both EP-002 intake and EP-004 operations.
- Delay in EP-002 blocks EP-003 clinical data intelligence stories.
- Delay in EP-003 blocks full EP-006 dashboard value realization.

Mitigation:
- Keep EP-007 and EP-005 done criteria as gate checks in Sprints 1-4.
- Reserve 10-15% sprint-level contingency for integration and compliance rework.
- Execute end-to-end integration checkpoints at Sprint 7, Sprint 11, and Sprint 14.

---

## 6. Load Balance Assessment

- Average load: 36 SP/sprint (504 / 14)
- Effective capacity target: 37 SP/sprint
- Over target (+): Sprint 1 (+2), Sprint 3 (+4), Sprint 5 (+1), Sprint 6 (+3), Sprint 8 (+1), Sprint 11 (+1), Sprint 12 (+1)
- Under target (-): Sprint 9 (-7), Sprint 10 (-2), Sprint 13 (-8), Sprint 14 (-7)

Assessment:
- Plan is feasible with buffer if under-loaded sprints absorb spillover and defect burn-down.
- Higher-load sprints are intentionally aligned to feature-heavy delivery windows.
- Sprint 13-14 provide controlled landing zone for stabilization, NFR tuning, and release readiness.

---

## 7. Coverage Report

### 7.1 Epic Coverage
- EP-001: 10/10 stories planned
- EP-002: 8/8 stories planned
- EP-003: 12/12 stories planned
- EP-004: 12/12 stories planned
- EP-005: 10/10 stories planned
- EP-006: 17/17 stories planned
- EP-007: 13/13 stories planned
- EP-008: 15/15 stories planned
- EP-TECH-001: 6/6 stories planned
- EP-DATA-001: 5/5 stories planned

### 7.2 Plan Completeness
- Story allocation completeness: 108/108 (100%)
- Dependency ordering: enforced at epic level
- Capacity model: applied with 15% buffer
- Critical path: identified and mapped to sprint windows

---

## 8. Recommended Next Steps

1. Validate squad-level ownership split for each sprint backlog.
2. Run dependency review workshop for Sprint 1-4 gate stories (EP-005, EP-007, EP-TECH-001).
3. Convert this plan into task-level execution using /plan-development-tasks per user story batch.
4. Add project_plan.md back to this branch and re-baseline if schedule/cost constraints change.

End of document.
