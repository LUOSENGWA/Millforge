# Domain Fragment: Security (security)

> T2 domain fragment · source: reference | applies to: worker, critic | spawn domain: security

## Context Input (spawn reads from files)

- audit object inventory (code/config/dependencies, file references)
- threat-model boundary (what this task defends against / what it does not — a 12-REDLINES boundary declaration)
- existing security control inventory (baseline)

## Execution Constraints

- **zero credential residue**: tokens/keys never enter artifacts/conversation/logs; found = escalate immediately (I3)
- scans = reproducible commands (tool + version + parameters into the scorecard)
- vulnerability report format: location + reproduction steps + impact surface + recommendation (each an independent artifact entry)
- fix verification: same command before/after comparison (complete evidence chain)
- a security configuration change = R1 (human-locked)

## Acceptance Points (critic perspective)

- each item reproduced (the report's reproduction steps must actually run)
- false-positive filtering: anything tagged "false positive" must carry a reason (not skipped)
- the fix introduces no regression (impact-surface check)
- boundary honesty: declare "this audit does not cover X" (never pretend full coverage)
