# UNIT-TEST-PLAN-078: Audit Log Query Interface (Admin Only)

User Story: US-078 (EP-007)
Source File: .propel/context/tasks/EP-007/us_078/us_078.md
Priority: HIGH
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for admin-only audit querying, including filter/pagination behavior, record detail rendering, export correctness, and unauthorized access blocking.

---

## 2. Scope and Assumptions

### In Scope
- Admin-only authorization checks for query interface.
- Filtered query behavior with pagination and sorting.
- Detailed metadata view for selected audit records.
- CSV/JSON export behavior and content parity checks.
- Unauthorized access handling with 403 response.

### Out of Scope
- Full audit analytics dashboards.
- External audit platform integrations.

### Assumptions
- Query API and UI state are testable via mocked repository/services.
- Export formatter is a separate module with unit-testable outputs.

---

## 3. Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criterion | Unit Test Coverage |
|---|---|---|
| AC-1 | Only authorized Admin users can access interface | UT-078-001, UT-078-002 |
| AC-2 | Filter criteria return matching records with pagination | UT-078-003, UT-078-004 |
| AC-3 | Selected record shows full metadata details | UT-078-005, UT-078-006 |
| AC-4 | Export downloads as CSV or JSON | UT-078-007, UT-078-008 |
| AC-5 | Unauthorized access receives 403 Forbidden | UT-078-009, UT-078-010 |

---

## 4. Unit Test Areas

### UT-078-001: Admin role passes query interface authorization guard
- Mock admin principal.
- Assert interface and query endpoints accessible.

### UT-078-002: Non-admin role is denied interface access
- Mock non-admin principal.
- Assert access blocked.

### UT-078-003: Filter query builder maps actor/action/date/resource/result to API params
- Apply filter combinations.
- Assert generated query payload correctness.

### UT-078-004: Pagination and sorting return deterministic subsets
- Mock paginated dataset.
- Assert page boundaries, counts, and sort order behavior.

### UT-078-005: Record selection shows actor/resource/action/timestamp/outcome metadata
- Select row fixture.
- Assert detail panel fields are complete and correctly mapped.

### UT-078-006: Missing optional metadata fields display safe fallback values
- Provide partial record fixture.
- Assert non-breaking fallback rendering.

### UT-078-007: CSV export output matches current filtered result set
- Mock filtered results and export action.
- Assert row count/content parity with visible dataset.

### UT-078-008: JSON export output preserves schema and policy-compliant fields
- Trigger JSON export.
- Assert structure and allowed field set.

### UT-078-009: Unauthorized API query attempt returns 403
- Simulate direct query API call with unauthorized principal.
- Assert 403 response.

### UT-078-010: Unauthorized export attempt is blocked with 403
- Simulate export endpoint access by unauthorized principal.
- Assert 403 and no payload leak.

### UT-078-011: Read-only enforcement blocks mutation operations in query interface scope
- Attempt create/update/delete via interface routes.
- Assert method/permission denial.

### UT-078-012: Query performance guardrails apply default limits
- Assert default page size/max limit safeguards for large result requests.

---

## 5. Test Data and Mocking Strategy

- Fixtures: admin/non-admin identities, audit query datasets, partial metadata records, export outputs.
- Mocks: RBAC authorizer, query repository, pagination adapter, export formatter.

---

## 6. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-078-001 through UT-078-010.

---

## 7. Suggested File Layout

- tests/unit/audit/AuditQueryAuthorization.test.ts
- tests/unit/audit/AuditQueryFilterPagination.test.ts
- tests/unit/audit/AuditQueryDetailView.test.tsx
- tests/unit/audit/AuditQueryExport.test.ts
- tests/unit/audit/__fixtures__/auditQuery.fixtures.ts

---

## 8. Definition of Done (Unit Test Plan)

- [ ] Test cases UT-078-001 through UT-078-012 implemented.
- [ ] AC-1 through AC-5 traceability retained.
- [ ] Coverage and CI reliability targets met.
