# GOV-2: Versioning and Deprecation Policy

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Approvals:** Architecture Review (Pending)

---

## 1. Overview

This document establishes the API versioning strategy and deprecation policy. It defines:
- Version numbering and lifecycle management
- Breaking vs. non-breaking changes classification
- Deprecation process and timelines
- Migration and support strategies
- Communication requirements

All API versions MUST follow this policy to ensure predictable, backward-compatible upgrades.

---

## 2. Versioning Strategy

### 2.1 Semantic Versioning

All APIs follow Semantic Versioning (MAJOR.MINOR.PATCH):

| Component | Incremented | When | Example |
|-----------|------------|------|---------|
| MAJOR | Breaking change | Incompatible changes | 1.0.0 → 2.0.0 |
| MINOR | Non-breaking addition | New features, new endpoints | 1.0.0 → 1.1.0 |
| PATCH | Bug fix | Fixes without API changes | 1.0.0 → 1.0.1 |

### 2.2 URL-Based Versioning (Preferred)

```
https://api.propellq.local/api/v1/appointments
https://api.propellq.local/api/v2/appointments
```

### 2.3 Header-Based Versioning (Alternative)

For clients that cannot change URLs:

```
GET /api/appointments
Accept: application/vnd.propellq.v1+json
X-API-Version: 1.0.0
```

### 2.4 Version Lifecycle

Every API version follows this lifecycle:

```
┌─────────────┐      ┌──────────────┐      ┌────────────┐      ┌───────┐
│   CURRENT   │──6mo─│  DEPRECATED  │──6mo─│  SUNSET    │──1mo─│ GONE  │
│  (Latest)   │      │   (Active)   │      │(Read-only) │      │       │
└─────────────┘      └──────────────┘      └────────────┘      └───────┘
- New features       - Still supported      - No new clients   - Server
- Bug fixes          - Critical fixes only  - Read-only ops    - returns
- Support ticket priority: HIGH             - Priority: LOW    - 410 Gone
```

| Phase | Duration | Status | Support | Operations |
|-------|----------|--------|---------|------------|
| **CURRENT** | Until next major | Latest version | Full support, bug fixes | All (read/write) |
| **DEPRECATED** | 6 months | Actively supported | Bug fixes, security fixes | All (read/write) |
| **SUNSET** | 1 month (final notice) | Limited support | Critical fixes only | Read-only |
| **GONE** | After sunset | No support | None | HTTP 410 Gone |

---

## 3. Breaking vs. Non-Breaking Changes

### 3.1 Breaking Changes (Require Major Version)

The following changes are **BREAKING** and require MAJOR version increment:

| Change | Example | Version |
|--------|---------|---------|
| Remove endpoint | DELETE /api/v1/appointments | 1.0 → 2.0 |
| Rename field | patientId → patient_id | 1.0 → 2.0 |
| Change field type | age: "25" → age: 25 | 1.0 → 2.0 |
| Remove required parameter | name (required) → name (optional) in response | 1.0 → 2.0 |
| Change HTTP method | POST /update → PATCH /update | 1.0 → 2.0 |
| Change error code | VALIDATION_ERROR → INVALID_INPUT | 1.0 → 2.0 |
| Change status code | 201 Created → 200 OK | 1.0 → 2.0 |
| Add required field to request | Add required "tenantId" | 1.0 → 2.0 |
| Change response structure | data: {} → result: {} | 1.0 → 2.0 |
| Remove authentication | Add [Authorize] attribute | 1.0 → 2.0 |

### 3.2 Non-Breaking Changes (MINOR Version)

These changes are **NOT BREAKING** and use MINOR version increment:

| Change | Example | Version |
|--------|---------|---------|
| Add endpoint | POST /api/v1/appointments/batch | 1.0 → 1.1 |
| Add optional field to response | "metadata": {...} (new) | 1.0 → 1.1 |
| Add optional parameter | page_size=100 (now optional) | 1.0 → 1.1 |
| Add optional field to request | "notes": "text" (optional) | 1.0 → 1.1 |
| Change internal implementation | Database query optimization | 1.0 → 1.1 |
| Loosen validation | Email regex now allows + signs | 1.0 → 1.1 |
| Add new error code (no removal) | New error: "DUPLICATE_REQUEST" | 1.0 → 1.1 |
| Tighten error responses | More detailed error messages | 1.0 → 1.1 |
| Extend enum | New status value ARCHIVED | 1.0 → 1.1 |

### 3.3 Patch Changes (Bug Fix)

PATCH versions for bug fixes without API changes:

| Change | Example | Version |
|--------|---------|---------|
| Fix incorrect behavior | Sort order now ascending as documented | 1.0 → 1.0.1 |
| Security fix | Fix SQL injection vulnerability | 1.0 → 1.0.1 |
| Performance fix | Reduce query latency | 1.0 → 1.0.1 |
| Documentation fix | Clarify API behavior | 1.0 → 1.0.1 |

---

## 4. Deprecation Process

### 4.1 Deprecation Timeline

Minimum 6-month deprecation period for each major version:

```
Month 0: v2.0 Released
  ├─ v1.0 status: CURRENT → DEPRECATED
  └─ Announcement: "v1.0 deprecated, sunset in 6 months"

Month 3: Mid-point notice
  ├─ Reminder email to API consumers
  ├─ Blog post: "3 months to migrate"
  └─ Support ticket priority reduced

Month 5.5: Final notice
  ├─ Email to all active v1.0 clients (48-hour notice)
  ├─ Status: DEPRECATED → SUNSET
  └─ Operations: Read-only mode active

Month 6: Sunset deadline
  ├─ All new requests to v1.0 return HTTP 410 Gone
  ├─ Status: SUNSET → GONE
  └─ No support provided
```

### 4.2 Deprecation Announcement Template

When releasing a breaking change:

```
Subject: API v1.0 Deprecation Notice - 6 Month Migration Window

Dear API Consumer,

We're announcing the deprecation of PropellQ API v1.0, 
effective [DATE]. v1.0 will reach end-of-life on [DATE + 6 MONTHS].

Timeline:
- Today: v1.0 marked DEPRECATED, v2.0 available now
- Month 3: Reminder email
- Month 5: Final notice (2-week warning)
- Month 6: v1.0 endpoints return HTTP 410 Gone

Migration Path:
The following endpoints have changed in v2.0:

BREAKING CHANGES:
- GET /api/v1/appointments → GET /api/v2/appointments
  - Field: patientId (v1) → patient_id (v2) [BREAKING]
  - New required: "tenantId"

NON-BREAKING ADDITIONS:
- New field: "metadata" (optional, defaults to null)
- New endpoint: POST /api/v2/appointments/batch-import

Migration Support:
- See migration guide: https://docs.propellq.local/v2-migration
- Schedule 1:1 migration call: support@propellq.local
- SDK updates available for: Python, JavaScript, Go, C#

Questions? Contact: api-support@propellq.local

Thank you,
PropellQ API Team
```

### 4.3 Header-Based Deprecation Warning

Servers MUST add deprecation headers to responses:

```http
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sun, 22 Jun 2026 00:00:00 GMT
X-API-Warn: "API v1 is deprecated. Migrate to v2 by 2026-06-22"
Link: </api/v2/appointments>; rel="successor-version"

{
  "statusCode": 200,
  "data": {...}
}
```

### 4.4 Deprecation Headers Specification

| Header | Format | Purpose | Example |
|--------|--------|---------|---------|
| `Deprecation` | true/false | Indicates API is deprecated | Deprecation: true |
| `Sunset` | HTTP date | When endpoint will be removed | Sunset: Sun, 22 Dec 2026 00:00:00 GMT |
| `X-API-Warn` | String | Human-readable warning | X-API-Warn: "Deprecated, use v2" |
| `Link` | RFC 5988 | Link to replacement resource | Link: </api/v2/appointments>; rel="successor-version" |

---

## 5. Backward Compatibility Guarantees

### 5.1 What We Guarantee

Within a major version (1.x.y), we guarantee:

✅ **Do guarantee:**
- All existing endpoints remain available
- Existing fields continue to work
- Response field order may change (client must not depend on order)
- New optional fields may be added to responses
- New optional parameters may be added to requests
- Status codes 2xx, 4xx, 5xx classes remain consistent
- Error codes remain consistent (no removal, only additions)

### 5.2 What We Don't Guarantee

❌ **Don't guarantee:**
- Response size (may increase with new fields)
- Latency (may improve or degrade)
- Field order in JSON
- Internal implementation details
- Undocumented behavior
- Behavior outside documented limits

---

## 6. Migration Support

### 6.1 Migration Resources

For each major version, provide:

- [ ] Migration guide with before/after examples
- [ ] Changelog documenting all changes
- [ ] Code samples in popular languages
- [ ] API diffs highlighting changes
- [ ] FAQs addressing common questions
- [ ] Video tutorial for complex migrations
- [ ] Sandbox environment for testing

### 6.2 Migration Checklist

Publish migration checklist for clients:

```markdown
# Migrating from v1 to v2

## Step 1: Update Base URL
- [ ] Change from /api/v1/ to /api/v2/

## Step 2: Update Field Names
- [ ] patientId → patient_id
- [ ] clinicianId → clinician_id
- [ ] appointmentType → appointment_type

## Step 3: Add Required Fields
- [ ] Add "tenant_id" to all POST requests

## Step 4: Test
- [ ] Update test suite
- [ ] Run against v2 sandbox environment
- [ ] Verify all endpoints working

## Step 5: Deploy
- [ ] Update API client library
- [ ] Update documentation
- [ ] Deploy to production
- [ ] Monitor error logs

## Step 6: Verify
- [ ] Monitor production metrics
- [ ] Compare v1 vs v2 traffic
- [ ] Confirm zero migration errors
```

### 6.3 Support Channel

During deprecation period:

- Email: api-support@propellq.local
- Slack: #api-migration channel
- Office hours: Tuesdays 3-5 PM
- Escalation: Technical architect on-call

---

## 7. Version Numbering Examples

### 7.1 Major Version Release

**Scenario:** Removing deprecated fields

```
Current: v1.4.2
Breaking change: Remove "deprecated_field"
Next version: v2.0.0

Deprecation announcement: "v1.0-v1.4 will sunset in 6 months"
```

### 7.2 Minor Version Release

**Scenario:** Adding new optional field

```
Current: v1.4.2
Change: Add optional "metadata" field to response
Next version: v1.5.0

Backward compatible: Existing clients unaffected
```

### 7.3 Patch Version Release

**Scenario:** Bug fix in sorting

```
Current: v1.4.2
Change: Fix sort order bug in collection endpoint
Next version: v1.4.3

No API changes: Bump patch only
```

---

## 8. Version Support Matrix

### 8.1 Support Timeline

```
v1.0 Released: 2026-01-01
├─ 2026-01-01 – 2026-06-01: CURRENT (6 months)
├─ 2026-06-01 – 2026-12-01: DEPRECATED (6 months)
├─ 2026-12-01 – 2026-12-15: SUNSET (read-only, 2 weeks)
└─ 2026-12-15+: GONE (HTTP 410 Gone)

v2.0 Released: 2026-06-01
├─ 2026-06-01 – 2027-06-01: CURRENT (12 months minimum)
└─ 2027-06-01+: DEPRECATED (next major on horizon)
```

### 8.2 Support by Version

| Version | Status | Support | Duration | End Date |
|---------|--------|---------|----------|----------|
| v1.0 | CURRENT | Full | 6 months | 2026-06-01 |
| v1.0 | DEPRECATED | Full | 6 months | 2026-12-01 |
| v1.0 | SUNSET | Limited | 2 weeks | 2026-12-15 |
| v1.0 | GONE | None | — | 2026-12-15+ |
| v2.0 | CURRENT | Full | Until v3.0 | TBD |

---

## 9. Communication Plan

### 9.1 Announcement Channels

**All major version releases must be announced via:**

- [ ] Email to all registered API consumers
- [ ] Blog post on developer portal
- [ ] Slack notification in #api-announcements
- [ ] Status page update
- [ ] GitHub releases/changelog
- [ ] In-app notification for web console users
- [ ] Support ticket auto-notification

### 9.2 Announcement Schedule

```
Month 0 (Release)
├─ Day 0: Release announcement + migration guide published
├─ Day 1: Blog post published
└─ Day 2: Email to all consumers

Month 3 (Mid-point)
├─ Reminder email: "3 months remaining"
└─ Support office hours dedicated to migration Q&A

Month 5 (Final notice)
├─ Email: "2 weeks until sunset"
├─ Blog: "Final migration guide update"
└─ Support: Priority migration support available

Month 6 (Sunset)
├─ Email: "Today is sunset day"
├─ Status page: "v1.0 deprecated" banner
└─ Support: Escalation line for emergencies
```

---

## 10. Exception and Emergency Cases

### 10.1 Emergency Deprecation

If security vulnerability or critical bug discovered:

1. **Immediate:** Publish security advisory with workarounds
2. **24 hours:** Release patch for affected versions
3. **1 week:** Announce accelerated deprecation timeline
4. **2 weeks minimum:** New deprecation deadline (even if < 6 months)

### 10.2 Extension Request

If business need requires extended support:

1. Contact API leadership with justification
2. Provide migration blockers/challenges
3. Proposed timeline for remediation
4. Cost impact analysis
5. Decision within 1 week

---

## 11. Governance and Review

### 11.1 Version Decision Gate

All major versions require approval from:

- [ ] API Architect (Technical feasibility)
- [ ] Product Manager (Business justification)
- [ ] Security Team (Security implications)
- [ ] DevOps Team (Infrastructure capacity)
- [ ] Customer Success (Customer impact)

### 11.2 Quarterly Review

Review versions and deprecation status quarterly:

- Are any versions past their planned sunset?
- Do migration guides need updating?
- Are consumers hitting support issues?
- Should any timelines be extended/accelerated?

---

## 12. Documentation Requirements

For each version released:

- [ ] Changelog with categorized changes (breaking, features, fixes)
- [ ] Migration guide with code examples
- [ ] API reference documentation
- [ ] Deprecation notice in all release notes
- [ ] Breaking changes clearly highlighted
- [ ] Timeline for sunset clearly stated

---

## 13. Implementation Checklist

Services MUST verify:

- [ ] Semantic versioning (MAJOR.MINOR.PATCH) implemented
- [ ] Version clearly stated in API responses
- [ ] Deprecation headers included for deprecated APIs
- [ ] Migration guide published before major release
- [ ] Sunset dates announced 6 months in advance
- [ ] Support timeline clearly communicated
- [ ] Version support matrix documented
- [ ] All stakeholders (product, security, devops) approve releases
- [ ] Quarterly review of version lifecycle
- [ ] Client notifications sent on schedule

---

## 14. Questions and Feedback

For questions about versioning policy:
- Open issue in: `.propel/context/standards/issues/`
- API leadership: api-leadership@propellq.local
- Next review date: Q3 2026
