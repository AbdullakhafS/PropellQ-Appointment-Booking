# Codebase Analysis: PropelQ Appointment Booking and Clinical Intelligence

## 1. Executive Summary
The repository currently contains two implementation tracks for overlapping healthcare capabilities:
- A Python WSGI application under app with SQLite storage and extensive endpoint coverage.
- A .NET 9 layered solution under src with ASP.NET Core API, EF Core SQL Server persistence, and domain-driven structure.

This creates strong feature experimentation velocity but introduces architectural fragmentation, duplicate domain logic, inconsistent security controls, and uncertainty about the production system of record.

Overall maturity by dimension:
- Architecture: Medium (good local structure per stack, weak cross-stack coherence)
- Security: Medium-Low (good crypto and TLS foundations, but permissive API surface and weak defaults remain)
- Performance: Medium (basic observability and health checks exist, limited production-grade execution model in Python)
- Data model: Medium (rich schemas and constraints, but split persistence strategy)
- Integrations: Medium (clear adapter intent, but uneven hardening and ownership)

## 2. Scope and Method
Assessment was based on static analysis of implementation and configuration files in:
- app Python runtime, API routing, persistence, and public UI.
- src .NET API/Application/Domain/Infrastructure projects.
- tests folders for coverage signals.
- .propel context docs for intended architecture.

No full end-to-end runtime benchmark or full automated test execution was performed as part of this analysis run.

## 3. Architecture Assessment

### 3.1 Current System Shape
The codebase is effectively bifurcated:
- Python stack is currently operational and user-facing with role portals and a large route surface in app/src/web_app.py.
- .NET stack defines a clean layered architecture (Domain, Application, Infrastructure, Api) with SQL Server and EF Core.

Key observation:
- Product capabilities exist in both stacks but are not clearly partitioned by bounded context; many concepts overlap (intake, appointments, queue, security).

### 3.2 Strengths
- Python stack has broad feature completeness and many supporting modules (audit, lifecycle, logging, search, booking, MFA).
- .NET stack uses clean project boundaries and DI with AddInfrastructure extension.
- Infrastructure concerns are explicit (queue, waitlist, storage, insurance, notifications).

### 3.3 Architecture Risks
1. Strategic ambiguity (Critical): no single authoritative runtime path for deployment.
2. Duplication risk (High): business rules can diverge between Python and .NET implementations.
3. Operational complexity (High): two data access patterns (SQLite vs SQL Server/EF Core) increase migration and support burden.

## 4. Security Posture

### 4.1 Positive Controls
- Password hashing and migration logic exist in app/src/rbac.py (bcrypt + legacy PBKDF2 compatibility).
- Session token signature and inactivity handling are implemented in app/src/rbac.py.
- TLS middleware and HSTS header enforcement are present in app/src/tls_middleware.py.
- PHI/secret redaction frameworks are present in app/src/logging_redaction.py.
- MFA enrollment and verification capabilities are present in app/src/mfa_service.py.

### 4.2 High-Risk Gaps
1. Open CORS in .NET API (High)
- src/PropelIQ.Api/Program.cs currently configures AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader().
- Not acceptable for production PHI/PII workloads.

2. Missing authorization attributes in .NET controllers (High)
- Controllers expose endpoints without explicit [Authorize] role policy enforcement.
- Authorization middleware is enabled, but endpoint policy-level enforcement is not visible.

3. Weak secret fallback in Python token encryption path (High)
- app/src/booking_service.py uses default PROPELLQ_TOKEN_SECRET fallback value propellq-demo-secret.
- Production boot should fail fast when secret is absent.

4. Development demo account seeding in application startup (Medium)
- app/src/web_app.py seeds hard-coded demo users during create_app().
- Must be explicitly gated to local/dev mode only.

## 5. Performance and Scalability

### 5.1 Positive Signals
- Python app tracks query latency percentiles via SearchMetrics in app/src/web_app.py.
- Health endpoints exist (/health/live, /health/ready) with readiness gate checks.
- .NET stack uses async patterns and cancellation tokens in service interfaces.

### 5.2 Constraints and Bottlenecks
1. Python runtime model limits throughput scaling (High)
- app/server.py uses wsgiref.simple_server, suitable for local/dev but not production load.

2. SQLite as active Python backing store (High)
- app/src/db.py and app/db/schema.sql indicate single-file SQLite persistence.
- Concurrency and operational resiliency are limited for multi-user production traffic.

3. Large route monolith in Python web_app (Medium)
- app/src/web_app.py centralizes many concerns and endpoint handlers.
- Increased maintenance cost and regression risk as feature count grows.

## 6. Data Model and Persistence

### 6.1 Strengths
- Python schema includes meaningful constraints (status enums via CHECK, FK references, uniqueness).
- .NET EF Core model in src/PropelIQ.Infrastructure/Data/AppDbContext.cs defines rich entities and indexes.
- Data lifecycle, audit, reminders, and sync queues are modeled explicitly.

### 6.2 Data Architecture Risks
1. Split data platforms (Critical)
- Python flow: SQLite schema and seed data.
- .NET flow: SQL Server EF Core migrations.
- No authoritative migration bridge is defined between both active execution tracks.

2. Cross-stack contract drift risk (High)
- Entity names and behaviors may diverge over time without shared contract governance.

## 7. Integration Topology
Current integration topology includes:
- AI/LLM: OpenAI client usage in .NET chatbot service (src/PropelIQ.Infrastructure/Chatbot/ChatbotService.cs).
- Calendar integration: Google/Outlook authorization and sync flows in Python booking and API routes.
- Notification and queue orchestration: modeled in both stacks (not uniformly wired).

Integration risks:
- Ownership ambiguity for integrations due to duplicated domain capabilities.
- Inconsistent hardening and observability conventions across stacks.

## 8. Testing and Quality Signals
- Python test surface is broad under app/tests with many feature-focused test modules.
- .NET test project exists (tests/PropelIQ.Tests) but currently appears scaffold-level with no test .cs files detected in the folder inventory.

Implication:
- Test maturity is currently concentrated in Python; .NET path needs substantive test implementation before production confidence.

## 9. Prioritized Findings

### Critical
1. Dual authoritative runtime and persistence strategy without a clear production system of record.

### High
1. Overly permissive CORS in .NET API.
2. Missing explicit endpoint authorization policy enforcement in .NET controllers.
3. Default secret fallback for encryption token derivation in Python.
4. SQLite active runtime for production-like clinical scheduling workloads.

### Medium
1. Startup demo account seeding should be environment-gated.
2. Route concentration and monolithic handler growth in Python web_app.
3. .NET testing implementation lagging behind project structure.

## 10. 30/60/90 Day Remediation Plan

### 0-30 Days (Stabilize and Secure)
1. Declare single production runtime of record (Python or .NET) and freeze feature duplication.
2. Remove permissive CORS wildcard in .NET and enforce environment-specific origins.
3. Add explicit auth policy attributes to all protected .NET endpoints.
4. Enforce fail-fast startup when PROPELLQ_TOKEN_SECRET is unset outside local development.
5. Gate demo account seeding behind explicit local development flag.

### 31-60 Days (Consolidate and Align)
1. Publish canonical domain and API contract boundaries for appointments, intake, queue, and audit.
2. Establish one persistence strategy for production and create migration/deprecation plan for the other.
3. Decompose Python web_app endpoint router into bounded route modules if Python remains primary.
4. Add baseline .NET API security and integration tests if .NET remains on roadmap.

### 61-90 Days (Scale and Operate)
1. Move Python serving stack to production-grade WSGI/ASGI hosting if Python is retained.
2. Add SLO dashboards and alerting for p95 latency, auth failures, queue lag, and sync errors.
3. Introduce architecture decision records for integration ownership and data governance.
4. Run failover/load/security drills against the chosen production stack.

## 11. Immediate Quick Wins
1. Fix malformed public landing file content in app/public/index.html (legacy content currently appended after closing html).
2. Replace wildcard CORS policy with named policies and allowed origins in src/PropelIQ.Api/Program.cs.
3. Add production secret validation checks in app/server.py and app/src/booking_service.py paths.
4. Add test placeholders and first integration test suite in tests/PropelIQ.Tests to validate API auth and core flows.

## 12. Conclusion
The repository demonstrates strong engineering effort and breadth of functionality. The dominant risk is not missing features; it is architectural split-brain between two partially complete platforms. Resolving platform authority and security hardening first will unlock safer scale, lower operational risk, and clearer delivery velocity.
