# UNIT-TEST-PLAN-021: Extract Structured Data from PDF and DOCX

User Story: US-021 (EP-003)
Source File: .propel/context/tasks/EP-003/us_021/us_021.md
Priority: CRITICAL
Status: Planned
Created: 2026-06-19

---

## 1. Objective

Define unit test coverage for structured-data extraction from PDF/DOCX parsing outputs, including field recognition, normalization, confidence scoring, and fallback handling.

## 2. Scope and Assumptions

### In Scope
- Parser output adapters.
- Field extraction rules for meds/allergies/diagnoses/demographics.
- Confidence score calculation and thresholds.
- Missing/ambiguous extraction fallback behavior.

### Out of Scope
- Raw OCR model correctness.
- End-to-end storage/integration tests.

### Assumptions
- Extraction engine receives tokenized parser outputs.
- Rules are deterministic and testable with fixtures.

## 3. Acceptance Criteria to Test Mapping

| AC ID | Unit Test Coverage |
|---|---|
| AC-1 to AC-3 parser mapping | UT-021-001, UT-021-002 |
| AC-4 to AC-6 extraction confidence | UT-021-003, UT-021-004 |
| AC-7 to AC-9 fallback/unknowns | UT-021-005, UT-021-006 |

## 4. Unit Test Areas

### UT-021-001: PDF parser tokens map to canonical extraction fields
### UT-021-002: DOCX parser tokens map to canonical extraction fields
### UT-021-003: Normalization rules standardize date, dosage, and units
### UT-021-004: Confidence scorer returns expected bucket for clean vs noisy text
### UT-021-005: Ambiguous values are flagged for manual review
### UT-021-006: Missing required entities return partial result with warnings
### UT-021-007: Extraction preserves source offsets/references for traceability
### UT-021-008: Unsupported section text is safely ignored without crash

## 5. Coverage Targets

- Statements: >= 85%
- Branches: >= 80%
- Functions: >= 85%
- Lines: >= 85%

Critical-path requirement:
- 100% pass rate for UT-021-001 through UT-021-006 before merge.

## 6. Suggested File Layout

- tests/unit/clinical/extraction/PdfDocxExtractionMapping.test.ts
- tests/unit/clinical/extraction/ExtractionConfidenceFallback.test.ts
- tests/unit/clinical/extraction/__fixtures__/extraction.fixtures.ts

## 7. Definition of Done (Unit Test Plan)

- [ ] Unit test plan approved for US-021.
- [ ] Test cases UT-021-001 through UT-021-008 implemented.
- [ ] Coverage targets achieved.
- [ ] CI unit-test stage passes.
