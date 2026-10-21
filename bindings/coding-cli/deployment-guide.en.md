# Deployment Guide (Claude Code / coding-CLI Binding, exclusive)

> This file is the deployment/invocation specification of `bindings/coding-cli/`; the mapping is in `mapping-table.md`.
> Positioning: this binding has no platform layer and no identity-file concept — "deployment" = the invocation convention + the evidence-chain acceptance; the 4 missing capabilities are all carried by the parent execution unit.

## 1. Topology

| Primitive | Deployment form |
|------|---------|
| this runtime | the coding-CLI process (one-shot), invoked by the parent execution unit |
| parent execution unit | an AgentTeams worker / a bare-qwenpaw agent (provides CAP-STATE / CAP-TIMER / CAP-NOTIFY / CAP-ROSTER) |
| state | the parent execution unit's CAP-STATE (this runtime is stateless) |
| store | the coding-runs API + local workspace files |
| timer / notify / roster | not applicable (provided by the parent execution unit) |
| identity file | none (protocol constraints are carried in three places: the task spec + the invocation parameters + the parent execution unit's identity file) |

## 2. Invocation Chain (compile → invoke → accept)

```
parent execution unit
  → construct the task spec (core/schemas/spec.schema.json)
  → invoke the coding-CLI (one-shot; flags include --max-wall-time + --approval-mode)
  → exit 0: read the coding-runs evidence chain → fingerprint verification (CAP-STORE T2) → accept
  → exit 55: bounded_failure (logged to decision_log; escalation after ≤3 times)
  → others: failure (same as above)
```

**Hard constraints**:
- `--max-wall-time` must be set (X4: boundedness is this binding's core contract; an unbounded invocation = a non-compliant invocation).
- critical_delivery (R1 class): **yolo forbidden** (see `skill-fragments.md` §4).
- No SOUL.md deployment (the CLI has no identity-file concept).

## 3. Sync Layer

not applicable — there is no async sync layer; local read-after-write strong consistency.

## 4. Failure Sequences and Recovery

| Failure | Detection | Recovery |
|------|------|------|
| execution timeout | exit 55 | bounded_failure: logged to decision_log; escalation after ≤3 times (the parent execution unit re-dispatches) |
| execution failure (other non-zero exit) | the exit code | same as above (failure semantics; decision_log) |
| artifact fingerprint mismatch | the coding-runs checksums vs the returned fingerprint | reject acceptance; the three-layer review chain (see `skill-fragments.md` §3) |
| approval timeout / no response | no reply to the approval prompt | the parent's CAP-TIMER judgement + the persistent display surface as fallback (this binding's approval surface = the synchronous prompt; the W5 persistent surface is the parent's responsibility) |
| state loss | not applicable (this runtime is stateless) | the state is in the parent execution unit's CAP-STATE; recovery follows the parent execution unit's mechanism |
| runtime version drift (flag behavior change) | TBD | TBD (the runtime version matrix declaration is not provided) |
