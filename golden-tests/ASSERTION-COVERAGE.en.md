# Assertion Coverage (ASSERTION-COVERAGE.en)

> This file is updated as assertions are added; `PRODUCTION-BASELINE.md` is frozen and must not be modified.
> Assertion entry point: `golden-tests/scripts/run-scripts-tests.sh` (section 10 "assertion completion", PASS 54 → 83).
> Principle: every assertion value is taken from the existing output of `core/scripts/` and `core/schemas/` (exit codes / stdout JSON fields); the runner is zero-LLM and dependency-free (python3 stdlib only).
> Purpose: explicitly separate protocol behaviors that are deterministically assertable from those that are unassertable due to a missing carrier, preventing the "assumed covered" illusion.

## A. Design-review risk points (10)

| # | Risk point | Current state | Disposition |
|---|---|---|---|
| 1 | decision_log physical location + schema validation layer | ✅ Covered (validate-decision-log, 5 cases: valid / schema violation / over-limit without truncated / truncated+contract_touch / parse failure) | — |
| 2 | Where merge-conflict detection executes | ✅ Covered (detect-conflict, 5 cases: shared surface 22 / hard conflict 20 / assumption conflict 21 / dimension mismatch 20 / no overlap 0) | — |
| 3 | Contract version pinning (minor/major) | ✅ Covered (contract-revalidate, 5 cases: none 0 / minor 30 / major 31 / report missing 32 / semver line cross 31) | — |
| 4 | R5 locker timeout (weight demotion, not default consent) | ✅ Covered: existing irreversible 81/block case; this batch adds 3 cases (B-4 late-reply demotion 2.0→1.0, reversible timeout=wait, defer recorded as dissent, out of denominator) | New 10.1–10.3 |
| 5 | R6 stall accumulation (2 escalations / 3 freezes) | ✅ Covered (attention-stall, 5 cases: 3 stale 41 / 2 stale 40 / 1 fresh 0 / human response 0 / meta missing 42) | — |
| 6 | critic vs human spec-lock deadlock (24h final ruling) | ⚠️ Partial: verification-mismatch-window covers the 24h window side (B-6); final ruling authority is protocol-level behavior, not script behavior | Blocked (missing carrier: 24h final-ruling record format or adjudication script; needs a new core script or protocol rule) |
| 7 | Production team migration path | ❌ Unassertable (process/ops domain, not protocol-compiler behavior) | out-of-scope |
| 8 | multi_user × NMH routing | ❌ Unassertable (routing semantics belong to the planned binding-layer mapping table; the protocol compiler does not emit routing) | out-of-scope (assertable once the binding mapping table lands) |
| 9 | contract owner independence (2W rule) | ❌ No carrier: no rule script / compiler rule checks independence between contract owner and consumer | Blocked (missing carrier: a contract-owner-independence compiler rule) |
| 10 | decision_class misclassification (saga compensation) | ✅ Covered (saga-compensate, 5 cases + consistency-check, 6 cases) | — |

## B. Protocol assertions: signal + multi-critic (6)

| Assertion | Current state | Disposition |
|---|---|---|
| signal ① acceptance fails when "completed" is not marked | ❌ No acceptance script carrier | Blocked (missing carrier: an acceptance gate script validating the completion-mark signal; needs a new core script) |
| signal ② signal set identical after hard reset | ❌ No state-machine scenario test skeleton | Blocked (missing carrier: state-transition scenario fixtures + re-run comparison script, or a state-machine test harness) |
| signal ③ zero is_signal=false in review refs | ✅ Covered: this batch adds 3 schema-level cases on `signal_event.schema.json` (required + closed event_type list; values read from the schema file, no second hardcoded list) | New 10.4 |
| multi-critic ① a single model family must not pass as multi-critic | ⚠️ Carrier exists (`critic_model_family` in `scorecard.schema.json`), rule not scripted | This batch adds 3 schema-level cases (valid with value 0 / absent is legal 0 / missing required 1); the ≥2-families rule is Blocked (missing carrier: a multi-critic aggregation rule script) |
| multi-critic ② a tie must escalate to a human | ✅ Covered: existing tie=80 case + this batch adds a `next=escalate` assertion | Existing section 8 case + new assertion |
| multi-critic ③ minority dissent must be recorded | ✅ Covered: this batch adds 3 cases (defer=abstain recorded in dissent, counted approve votes recorded as minority on reject, defer counted in denominator when blocked) | New 10.3 / 10.7 / 10.8 |

## C. Blocked items (missing carrier / what is needed to assert)

| Item | Missing carrier | Needed to assert |
|---|---|---|
| signal ① | acceptance gate script | a new core script (validate the completion-mark signal at acceptance) + golden scenario |
| signal ② | state-machine scenario skeleton | hard-reset scenario fixtures + signal-set re-run comparison script (or a state-machine test harness) |
| multi-critic ① (rule level) | multi-critic aggregation rule script | a new core script: ≥2 `critic_model_family` check (schema-level carrier already pinned by this batch) |
| risk point 6 | 24h final-ruling record/script | a ruling record format (or adjudication script) + golden scenario |
| risk point 9 | contract owner independence compiler rule | compiler rule: owner ≠ consumer (2W) check |

## D. Notes on assertion values (deviations from the initial spec wording)

All exit codes / field values follow the actual measured output of `core/scripts/` and `core/schemas/` as of this commit. Where the initial spec wording diverged from measured behavior, the tests follow the measured behavior:

1. **Case 10.3 (R2 defer tie)**: the tie path deterministically exits 80 (`s_a==s_r → tie/escalate/80`). The initial spec said 0; corrected to 80 (consistent with the existing tie=80 case and the tie→escalate semantics of multi-critic ②).
2. **Case 10.5 (scorecard)**: `critic_model_family` is not in the schema's `required` (single-critic scorecards legitimately omit it), so an absent field is asserted → 0 (pinning carrier optionality); a separate negative case for a truly required field (missing `verdict` → 1) pins the required set. The initial spec said "missing critic_model_family → 1"; corrected against the actual schema.
3. **Case 10.8 (blocked-state defer counted in denominator)**: the initial spec left the exit code unspecified; measured value is 80 — counting defer in the denominator flips a would-be pass into a tie, which is exactly the observable evidence of B-5, so the test asserts 80.
