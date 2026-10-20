# core/ — Protocol Layer v1.0 (Apache-2.0)

> Runtime-agnostic protocol semantics + deterministic implementation + compiler + template library + regression tests.
> **Generic-term discipline**: this directory allows only CAP-* capability ids + generic terms (child agent / parent executor / main session / persistent display surface / runtime scheduler / object store / notification channel / decision record / state store / timer).
> Runtime-specific names (spawn_subagent, cron, mc, dashboard, Matrix, MinIO/RustFS…) are allowed **only in the `bindings/` layer**.

## Directory

```
core/
  protocol/          protocol clauses (13 files, v1.0 frozen baseline)
    00-OVERVIEW      general: positioning / principles P1-P8 / document map / version policy / non-goals
    01-PRIMITIVES    15 primitives + role invariants
    02-MODES         single_user / multi_user phase transition
    03-DECISIONS     R1-R6 + decision_log + closed type set
    04-NMH           human↔agent collaborative exploration (explore / lock / seven questions / evolution)
    05-NMA           peer review (checklist / peer review / multi-critic MC-1~10 / B-6)
    06-LIFECYCLE     recursive decomposition / completion signal / dual channel / declare-verify / failure SOP
    07-HANDOFF       cross-team (compiled in single_user only)
    08-CONTRACT      contract pinning + structured spec
    09-GOVERNANCE    voting / arbitration / state mapping (B-4/B-5/B-8/C-3)
    10-LOOP          the 14th primitive: loop_spec / five phases / driver / anti-bypass
    11-SIGNAL        the 15th primitive: 7 closed markers / three effects / layered reset
    12-REDLINES      safety redlines S1-S5 / trust boundary / reliability layering / attention loading
  security.md        threat model + security chapter v1.0 (trust boundary / integrity mechanism matrix / 5 adversarial scenarios / minimum channel-identity requirements / escalation rules; bilingual)
  cost-model-tiering.md  protocol cost model + three tiers v1.0 (simple/standard/full; the tier is locked at spec creation; bilingual)
  production-harden.md   production hardening, 4 patches v1.0 (protocol versioning / native context budget / batched delegation / clock authority; bilingual)
  calibration/       calibration procedure (token-shadow-calibration v1.0, token shadow counting; bilingual)
  schemas/           JSON Schemas (11, consumed by the compiler's Validate stage)
  invariants/        state-machine invariants (task/decision/loop/attention, 4 files; bilingual)
  scripts/           8 deterministic scripts + timer-derive (the executable part of the protocol semantics)
  binding-contract.md 8-capability interface (CAP-STATE/STORE/TIMER/NOTIFY/ATTN/SPAWN/EXEC/ROSTER; bilingual)
compiler/            6-stage compiler (Validate→Assemble→Budget→Render→SelfCheck→Provenance)
templates/           template library (skeleton 4 + fragment 12 + domain 21 + industry 6; all bilingual X.md + X.en.md)
golden-tests/        L5 regression (T1-T10 / 13 cases / 83 script assertions + frozen baseline + production provenance)
bindings/            runtime bindings (agentteams reference binding / single-agent / coding-cli; products are matrix rows)
migration/           B-7 migration kit (scaffold-team.py skeleton generator + MIGRATION-CHECKLIST.md human confirmation list)
docs/                general documentation + provenance/ (verbatim source records)
```

## Migration Path (Strangler Fig, B-7)

**A team with hand-written SOULs is not rewritten from scratch** — it is replaced in three phases:

1. **Shadow**: write a `team.json` for the current team (start from the two reference instances in `golden-tests/fixtures/`: `example-biz-team.json` = single_user / `bizmarket-team.json` = multi_user), compile once, and diff against the existing SOULs (audit: which current-protocol clauses the new protocol does not cover).
2. **Parallel**: enable the newly compiled SOULs on part of the roles (new tasks on the new protocol, existing tasks on the old one).
3. **Cut**: switch over fully and archive the old SOULs.

The migration toolchain **ships with the release**: `migration/` (scaffold-team.py skeleton generator + MIGRATION-CHECKLIST.md human confirmation list). `golden-tests/fixtures/` provides 2 reference team.json files + 5 production-baseline SOULs (anonymized; see `golden-tests/PRODUCTION-BASELINE.md`).

## Version

- **Protocol v1.0** (frozen baseline, 2026-10-19): semantic changes = minor; primitive additions/removals or mode-definition changes = major
- Bindings are versioned independently and declare "compatible with Millforge v1.x"
- Old versions are archived, never deleted (audit chain)

## Provenance chain (recast traceability)

NMProtocol design v3.0 (721 lines, 2026-09-03 baseline)
+ eight rounds of DeepSeek review (2026-10-17~19, verbatim in media/, fully adopted + 4+3 corrections on our side)
+ production evidence (L4 retest 10 nodes / Manager five issues / #123 group history / #150 decision chain / #176 pydantic)
→ final documents: `AgentCom/千锻-DS审查分析-20261018.md` §A-W (workspace-only, not part of the open-source release)
