# DOC-2: Onboarding Materials Update - API Standards Integration

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Audience:** New engineers, engineering managers, onboarding coordinators

---

## 1. Overview

This document outlines updates to engineering onboarding materials to include PropellQ API standards training. All new engineers building or extending APIs MUST complete this onboarding before their first API implementation.

---

## 2. Onboarding Module: "API Standards Essentials"

### 2.1 Module Objectives

After completing this module, engineers will:

✅ Understand why API standards exist  
✅ Know the standard request/response envelope structures  
✅ Apply naming conventions correctly  
✅ Handle errors using standard error envelopes  
✅ Implement validation and authentication  
✅ Support idempotency for write operations  
✅ Use the service bootstrap package  
✅ Pass API conformance checks  

**Time Commitment:** 3-4 hours self-paced + 1-hour team walkthrough

---

## 3. Self-Paced Learning Path (3-4 hours)

### 3.1 Step 1: Understanding the Why (20 minutes)

**Objective:** Understand business value of standards

**Reading:**
- `.propel/context/standards/README.md` - Overview
- TASK-098 Objective and Scope sections

**Key Takeaway:**  
*API standards reduce integration defects, improve delivery speed, and enable reliable downstream automation.*

**Discussion:**
- Why should all APIs look and behave the same?
- What problems do we prevent with standards?

---

### 3.2 Step 2: Request/Response Envelopes (30 minutes)

**Objective:** Learn standard envelope structures

**Reading:**
- `api-contract-specification.md` § 2 (Request Envelope)
- `api-contract-specification.md` § 3 (Response Envelope)
- `api-contract-specification.md` § 4 (Error Envelope)

**Hands-On Exercise:**
```
Write JSON responses for these scenarios:
1. POST /api/v1/appointments returns 201 with new appointment
2. GET /api/v1/appointments returns 200 with appointment list
3. POST /api/v1/appointments with invalid data returns 400
4. GET /api/v1/appointments/{id} not found returns 404
```

**Answer Key:** See `api-standards-guide-service-bootstrap.md` § 4.1

**Key Takeaway:**  
*Every response has the same structure: statusCode, success, data/error, correlationId, timestamp.*

---

### 3.3 Step 3: Naming Conventions (20 minutes)

**Objective:** Apply correct naming conventions

**Reading:**
- `api-contract-specification.md` § 2.3 (Naming Conventions)
- `collection-semantics-standard.md` § 3 & § 4 (Query parameters and filters)

**Hands-On Exercise:**
```
Identify correct versions:
1. Request: patientName vs patient_name vs PatientName
2. Response field: firstName vs first_name vs FirstName
3. Enum: PENDING vs Pending vs pending
4. Query param: page_size vs pageSize vs page-size
5. Path: /appointments vs /appointment vs /Appointments
```

**Answer Key:**
- Request/Response fields: `firstName` (camelCase)
- Query params: `page_size` (snake_case)
- Enums: `PENDING` (SCREAMING_SNAKE_CASE)
- Paths: `/appointments` (plural, lowercase)

**Key Takeaway:**  
*Different contexts use different casing: fields are camelCase, parameters are snake_case, enums are SCREAMING_SNAKE_CASE.*

---

### 3.4 Step 4: Error Handling (30 minutes)

**Objective:** Handle errors using standard envelopes

**Reading:**
- `api-contract-specification.md` § 4 (Error Response Envelope)
- `api-contract-specification.md` § 7 (Status Code Mapping)
- `error-exception-middleware-contract.md` § 4 & § 5 (Validation & Auth errors)

**Hands-On Exercise:**
```
Map these scenarios to correct (status code, error code):
1. Missing required field → (400, VALIDATION_ERROR)
2. Invalid email format → (400, VALIDATION_ERROR)
3. No auth token → (401, UNAUTHORIZED)
4. Missing permission → (403, FORBIDDEN)
5. Appointment not found → (404, NOT_FOUND)
6. Duplicate appointment → (409, RESOURCE_CONFLICT)
7. Database timeout → (500, INTERNAL_SERVER_ERROR)
```

**Key Takeaway:**  
*Use standard error codes (VALIDATION_ERROR, UNAUTHORIZED, etc.) and include field-level error details.*

---

### 3.5 Step 5: Validation and Authentication (30 minutes)

**Objective:** Implement request validation and authentication

**Reading:**
- `validation-auth-middleware-contract.md` § 2 (Validation Middleware)
- `validation-auth-middleware-contract.md` § 3 (Authentication)
- `validation-auth-middleware-contract.md` § 4 (Authorization)

**Hands-On Exercise:**
```
Build a validator for "Create Patient" endpoint:
- Required fields: firstName, lastName, email, dateOfBirth
- Email must be valid format
- Date of birth must be reasonable (not future)
- Name fields max 100 characters
```

**Example Solution:** See `api-standards-guide-service-bootstrap.md` § 4.2

**Key Takeaway:**  
*Validation prevents bad data early. Use decorators/attributes (Authorize, RequirePermission) for auth.*

---

### 3.6 Step 6: Idempotency (30 minutes)

**Objective:** Support idempotent operations for write requests

**Reading:**
- `idempotency-middleware-pattern.md` § 2 & § 3 (Principles and header)
- `idempotency-middleware-pattern.md` § 7 (Client patterns)

**Hands-On Exercise:**
```
Scenario: User creates appointment with idempotency key "key-1"
- Request 1: POST /api/v1/appointments + X-Idempotency-Key: key-1
  Response: 201 Created with appointment-1

- Network timeout, client retries with same key
- Request 2: POST /api/v1/appointments + X-Idempotency-Key: key-1
  Response: ??? (What should happen?)

Answer: 201 Created with same appointment-1 (cached response)
Reason: Idempotency prevents duplicate creation on retries
```

**Key Takeaway:**  
*Idempotency keys ensure retried operations don't create duplicates.*

---

### 3.7 Step 7: Pagination and Collections (20 minutes)

**Objective:** Implement standard pagination

**Reading:**
- `collection-semantics-standard.md` § 2 (Pagination)
- `collection-semantics-standard.md` § 3 (Sorting)
- `collection-semantics-standard.md` § 4 (Filtering)

**Hands-On Exercise:**
```
Write pagination request/response for listing appointments:

Request:
GET /api/v1/appointments?page_number=2&page_size=20&sort_by=-createdAt&filter_status=CONFIRMED

Response:
{
  "data": [
    { "id": "apt-001", "status": "CONFIRMED", ... },
    ...
  ],
  "pagination": {
    "pageNumber": 2,
    "pageSize": 20,
    "totalItems": 150,
    "totalPages": 8,
    "hasNextPage": true,
    "hasPreviousPage": true,
    "firstItemNumber": 21,
    "lastItemNumber": 40
  }
}
```

**Key Takeaway:**  
*All collection endpoints support pageNumber, pageSize, sort_by, and filter_{field} parameters.*

---

### 3.8 Step 8: Correlation IDs and Logging (20 minutes)

**Objective:** Trace requests across services using correlation IDs

**Reading:**
- `api-contract-specification.md` § 8 (Correlation ID Propagation)
- `error-exception-middleware-contract.md` § 9 (Correlation ID Propagation)

**Hands-On Exercise:**
```
Trace this request:
1. Client sends: GET /api/v1/appointments with X-Correlation-ID: abc-123
2. Service A receives request, logs "CorrelationId: abc-123"
3. Service A calls Service B with X-Correlation-ID: abc-123
4. Service B logs "CorrelationId: abc-123"
5. Service B calls database, logs "CorrelationId: abc-123"
6. Service A returns response with correlationId: abc-123

Result: All logs contain same correlation ID, can trace request across services!
```

**Key Takeaway:**  
*Correlation IDs enable end-to-end request tracing for debugging.*

---

## 4. Practical Workshop (1 hour, Team-Led)

### 4.1 Workshop: Build Your First API

**Setup (10 minutes):**
```bash
git clone https://github.com/propellq/api-service-bootstrap.git \
  my-first-api
cd my-first-api
docker-compose up
```

**Build Endpoint (30 minutes):**

With facilitator guidance, build a complete endpoint:

```
1. Define request DTO (CreatePatientRequest)
2. Create validator (CreatePatientValidator)
3. Implement controller action (CreatePatient)
4. Run integration tests
5. Check API conformance linting
```

**Review and Q&A (20 minutes):**
- Show response envelope structure
- Demonstrate error handling
- Test idempotency
- Run conformance checks

---

## 5. Integration into Existing Onboarding

### 5.1 Before: Standard Onboarding Checklist

```markdown
# Engineering Onboarding Checklist

- [ ] GitHub access configured
- [ ] Development environment set up
- [ ] Codebase architecture walkthrough
- [ ] First pull request submitted
```

### 5.2 After: Updated Onboarding Checklist

```markdown
# Engineering Onboarding Checklist

## Week 1: Foundations
- [ ] GitHub access configured
- [ ] Development environment set up
- [ ] Codebase architecture walkthrough

## Week 2: API Development (NEW)
- [ ] **Completed API Standards Essentials module** ← NEW
- [ ] Built first API endpoint following standards
- [ ] Passed API conformance checklist
- [ ] Demonstrated understanding in peer code review

## Week 3: Delivery
- [ ] First pull request submitted
- [ ] Code review feedback addressed
- [ ] Ready for production work
```

---

## 6. Documentation Updates

### 6.1 New Wiki Page: "Building APIs at PropellQ"

**Suggested Location:** Engineering Wiki > Backend Development > Building APIs

**Content:**
```markdown
# Building APIs at PropellQ

## Quick Links
- [API Standards Overview](./standards/)
- [API Contract Specification](./standards/api-contract-specification.md)
- [Validation & Auth Contract](./standards/validation-auth-middleware-contract.md)
- [Service Bootstrap Package](https://github.com/propellq/api-service-bootstrap)
- [API Standards Video Tutorial](https://propellq.local/docs/api-standards-video)

## 5-Minute Quick Start
1. Clone service bootstrap
2. Create first endpoint following examples
3. Run conformance checks
4. Submit for review

## Common Questions
See [API Standards FAQ](./standards/faq.md)

## Support
- Email: api-support@propellq.local
- Slack: #api-development
- Office hours: Tuesdays 3-5 PM
```

### 6.2 Update "Developer Setup Guide"

**Before:**
```markdown
# Developer Setup

1. Install Docker
2. Clone repository
3. Run docker-compose up
```

**After:**
```markdown
# Developer Setup

1. Install Docker
2. Clone repository

### For API Development
3. **Review [API Standards Overview](./standards/)**
4. **Clone [API Service Bootstrap](https://github.com/propellq/api-service-bootstrap) as starting point**
5. Run docker-compose up
6. See [Building Your First API](./standards/api-standards-guide-service-bootstrap.md#section-4)
```

### 6.3 New FAQ Page

**File:** `.propel/docs/faq-api-standards.md`

```markdown
# API Standards FAQ

**Q: Do I have to follow all these standards?**  
A: Yes. All APIs MUST conform to standards. Exceptions require architecture review.

**Q: What if my use case doesn't fit the patterns?**  
A: Contact the API team. We may generalize the pattern or document an exception.

**Q: How do I get help implementing standards?**  
A: Email api-support@propellq.local or join #api-development Slack channel.

**Q: Can I skip idempotency for my endpoint?**  
A: No. All write operations (POST/PUT/PATCH) must support idempotency.

**Q: How long does it take to learn these standards?**  
A: 4 hours self-paced learning + 1 hour workshop. Less if you've done REST APIs before.

**Q: Are there examples in my language?**  
A: Yes. Bootstrap package includes C#, TypeScript, Python examples.

[See full FAQ](./standards/faq.md)
```

---

## 7. Role-Based Onboarding Tracks

### 7.1 New Backend Engineer

**Time:** 4 hours learning + 1 hour workshop

**Path:**
1. Self-paced learning (Sections 3.1-3.8)
2. Practical workshop (Section 4.1)
3. Build first endpoint with mentor
4. Code review by senior engineer

---

### 7.2 New Frontend Engineer (Consuming APIs)

**Time:** 1.5 hours learning

**Path:**
1. Read: Request/Response Envelopes (3.2)
2. Read: Naming Conventions (3.3)
3. Read: Error Handling (3.4)
4. Review: Client usage examples (Section 7)
5. Q&A: API team office hours

---

### 7.3 Engineering Manager

**Time:** 30 minutes overview

**Path:**
1. Watch: API Standards 5-minute overview video
2. Read: TASK-098 § 1-2 (Objective and Value)
3. Review: Onboarding checklist
4. Schedule: Quarterly API standards review with team

---

## 8. Ongoing Learning Resources

### 8.1 Monthly Lunch & Learn Sessions

**Topic Rotation:**
- Month 1: "API Design Pitfalls to Avoid"
- Month 2: "Debugging Common API Issues"
- Month 3: "Scaling APIs: Performance Best Practices"
- Month 4: "API Versioning and Deprecation in Practice"

**Format:**
- 30 minutes presentation
- 30 minutes Q&A and discussion
- Recorded for later viewing

---

### 8.2 Quarterly API Design Reviews

All new major API versions reviewed by standards committee:

- Technical architect
- Product manager
- Security lead
- Operations engineer

---

### 8.3 Documentation Maintenance

Standards documentation updated:
- **Monthly:** Based on team feedback
- **Quarterly:** Major reviews and pattern refinements
- **As-needed:** Security issues, critical bugs

---

## 9. Success Metrics

### 9.1 Engineer Competency

After onboarding, engineers should be able to:

- ✅ Build API endpoint from scratch following all standards
- ✅ Pass automated conformance checks
- ✅ Explain why each standard exists
- ✅ Identify and fix non-compliant code
- ✅ Mentor others on standards

### 9.2 Team Metrics

Team-wide standards adoption measured by:

| Metric | Target | Current |
|--------|--------|---------|
| % endpoints compliant | 95% | TBD |
| Avg time to build endpoint | -30% | TBD |
| Integration test pass rate | >98% | TBD |
| Security issues in APIs | 0 | TBD |

---

## 10. Rollout Timeline

### Phase 1: Week 1-2
- [ ] Onboarding materials finalized
- [ ] Wiki pages published
- [ ] Video tutorial recorded
- [ ] FAQ published

### Phase 2: Week 3-4
- [ ] New engineer training on standards
- [ ] First batch completes workshop
- [ ] Feedback collection and refinement

### Phase 3: Month 2
- [ ] All new engineers onboarded on standards
- [ ] First Lunch & Learn session
- [ ] API standards dashboard live

---

## 11. Checklist for Onboarding Coordinator

When onboarding new engineer working on APIs:

- [ ] Point to "API Standards Essentials" module
- [ ] Provide bootstrap package link
- [ ] Schedule workshop session (1 hour)
- [ ] Assign mentor for first endpoint
- [ ] Include API conformance checks in code review
- [ ] Collect feedback after first week
- [ ] Celebrate first production API endpoint! 🎉

---

## 12. Contact and Support

**Questions about onboarding?**
- Email: onboarding@propellq.local
- Slack: #new-engineers

**Questions about API standards?**
- Email: api-support@propellq.local
- Slack: #api-development
- Office hours: Tuesdays 3-5 PM

---

## 13. Additional Resources

- **Complete Standards:** `.propel/context/standards/`
- **Code Examples:** `api-service-bootstrap/examples/`
- **Video Tutorial:** https://propellq.local/docs/api-standards-video
- **OpenAPI Spec Example:** `api-service-bootstrap/examples/api-spec.openapi.json`
- **Troubleshooting:** `api-standards-guide-service-bootstrap.md` § 7

---

**Welcome to PropellQ! You're on the path to building world-class APIs.** 🚀
