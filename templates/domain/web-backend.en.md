# Domain Fragment: Web Backend (web-backend)

> T2 domain fragment · source: production | applies to: worker | spawn domain: web-backend

## Context Input (spawn reads from files)

- service architecture explanation + API route table (file references)
- code paths (refs) of the target interface/module + data model definitions
- test baseline (existing test inventory)

## Execution Constraints

- an interface change = a contract change (semver + dual confirmation S3); new interfaces go through the contract flow
- backward compatibility by default: before changing an interface, check the callers (grep the reference surface)
- error handling: error paths must have explicit handling (scorecard includes error-injection verification)
- tests: new/changed code = tests in sync (no tests = acceptance item ❌)
- database migration = R1 (human informed); rollback check for the migration

## Acceptance Points (critic perspective)

- interface verification = actual calls (curl/API client, with response evidence)
- concurrency surface: idempotency/race checks on write paths (verify when declared in the spec)
- security surface: input validation / injection surface / permission checks (crosses the security domain)
- regression: all existing tests green + impact-surface reference check
