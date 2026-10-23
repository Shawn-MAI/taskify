<!--
Sync Impact Report
Version change: 1.0.0 → 1.1.0
Modified principles: I. Security-First (added time-boxed Phase-1 authentication exception)
Added sections: none
Removed sections: none
Follow-up TODOs: none. Feature plans using the exception must name the scheduled
  follow-up auth feature (see Principle I).
-->

# Taskify Constitution

## Core Principles

### I. Security-First (NON-NEGOTIABLE)
Security is the highest-priority design constraint and overrides convenience and schedule.
Every feature MUST document its threat surface in its spec and plan. Secrets MUST NOT be
committed to source control; they MUST be supplied via a secret manager or environment
configuration. All services MUST enforce authentication and authorization on every endpoint
by default (deny by default), apply least privilege, and encrypt data in transit.

**Phase-1 Authentication Exception (time-boxed)**: A Phase-1 feature MAY omit end-user
authentication when its spec explicitly says so, and only while ALL of these hold:
- Every service stays token-authenticated: service-to-service calls MUST present a
  valid service credential, and requests without one MUST be rejected (deny by default at
  the service boundary).
- The unauthenticated user identity is documented as non-secure, and its risks are listed
  in the feature's threat surface.
- A follow-up feature that adds end-user authentication and authorization is scheduled,
  and the plan names it in its Complexity Tracking entry.
The exception expires when that follow-up feature ships, and it MUST NOT be applied to any
feature outside Phase 1. All other Principle I rules still apply.

Rationale: Taskify handles user and team data; retrofitting security is costly and risky.
The exception lets the first phase ship without login while keeping the service boundary
closed and the debt tracked.

### II. Mandatory Input Validation
All user input, and all data crossing a service boundary, MUST be validated on the server
side before use. Validation MUST use an explicit allow-list schema (type, length, format,
range) and reject non-conforming input with a safe error. Output MUST be encoded for its
context, and queries MUST be parameterized. Client-side validation is a usability aid only
and never a substitute. Each validation rule MUST have a test covering invalid input.
Rationale: Unvalidated input is the root cause of most injection and integrity flaws.

### III. Microservices Architecture
Taskify MUST be built as independently deployable services, each owning a single business
capability and its own data store. Services MUST communicate only through versioned,
documented contracts (APIs or events); direct access to another service's database is
prohibited. Inter-service calls MUST be authenticated, and each service MUST re-validate
inbound data (Principle II) rather than trusting peers. Contract changes that break
consumers MUST be versioned.
Rationale: Clear boundaries enable independent scaling, deployment, and security isolation.

### IV. Full Documentation (NON-NEGOTIABLE)
All code MUST be fully documented. Every public module, class, function, and API endpoint
MUST have documentation describing purpose, parameters, return values, errors, and security
considerations. Each service MUST have a README and a published API contract (e.g.,
OpenAPI). Documentation MUST be updated in the same change as the code it describes; a
change with missing or stale documentation MUST NOT be merged.
Rationale: Documentation keeps a distributed system understandable and auditable.

### V. Test-Driven Verification
Behavior MUST be covered by automated tests written before or alongside implementation.
Security-relevant paths (validation, authN/authZ) MUST have negative tests. Contract tests
MUST exist for every inter-service interface, and tests MUST pass in CI before merge.
Rationale: Tests are the evidence that security and contract guarantees actually hold.

## Security & Architecture Constraints

- Dependencies MUST be scanned for known vulnerabilities in CI; critical findings block
  release.
- Services MUST emit structured logs that never contain secrets or sensitive personal data.
- Errors returned to clients MUST NOT leak internal details such as stack traces.
- Each service MUST expose a health check and be containerized for independent deployment.
- Technology choices beyond these constraints are made per feature in its plan.

## Development Workflow & Quality Gates

- Every change MUST go through a peer-reviewed pull request.
- Reviewers MUST verify compliance with Principles I-V, including validation coverage and
  documentation completeness.
- Linting, tests, and security scans MUST pass before merge.
- Any deviation from a principle MUST be recorded with justification in the plan's
  complexity/compliance section and approved by a reviewer.

## Governance

This constitution supersedes all other practices. Amendments MUST be proposed in writing,
reviewed and approved by project maintainers, and include a migration plan for affected
specs, plans, and code. Versioning follows semantic versioning: MAJOR for backward
incompatible principle removals or redefinitions, MINOR for added principles or materially
expanded guidance, PATCH for clarifications and wording. Compliance MUST be checked in every
pull request review and reassessed at each feature planning phase.

**Version**: 1.1.0 | **Ratified**: 2026-10-23 | **Last Amended**: 2026-10-23
