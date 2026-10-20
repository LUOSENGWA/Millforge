# Domain Fragment: Infrastructure / Ops (infra-ops)

> T2 domain fragment · source: production (GPU inference cluster / containerized ops field work)
> Applies to: worker | spawn domain: infra-ops

## Context Input (spawn reads from files)

- topology diagram / node inventory + connection methods (file references; **credentials never enter conversation/artifacts** — terminal environment variables only)
- current state snapshot of the target system (`docker ps` / `df -h` / service status, with timestamps)
- change baseline (current configuration ref + fingerprint)

## Execution Constraints

- **check state before acting**: `docker ps` → API query → path verification → then act (never assume)
- destructive operations (restart/delete/production config change) = R1 human-locked; back up before the change (cp with timestamp, not "remembering to")
- rollback plan front-loaded: every change spec must contain "how to roll back" (no rollback = rejected)
- verification = system facts (command output / service status / logs); never inferred from "the command succeeded"
- batch operations (multi-node/multi-container) = single-point verification first, then full rollout (one node OK ≠ all OK)
- long outputs (logs/inventories) = written to files and referenced; never into conversation

## Acceptance Points (critic perspective)

- every change has before/after state comparison evidence (distinguishable timestamps)
- rollback path verified (actually tested where testable)
- impact surface: state check of other components depending on the service
- isolation boundary: the critic never executes change commands (read-only state checks limited to the 🔵 surface)
