# Changelog

All notable changes to the Millforge protocol compiler and reference bindings are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/); versions follow Semantic Versioning.

## [Unreleased]

### Added

- **NMA regains structured communication**: `05-NMA` split into Part A (8-message closed list + fields + 7 disciplines) / Part B (review); the `06-LIFECYCLE` dispatch triad = required `DELEGATE` fields.
- **NMH source discipline + execution-time ask**: §7 "no verifiable source" (fail-closed, abstention is legal); §8 structured decision requests (CAP-ATTN persistent surface + CAP-NOTIFY code-level event).
- **Context-window tiers (S/M/L)**: `12-REDLINES §5.1–5.4` (tier budgets + loading matrix + over-budget behavior).
- **21 new numbered entries in binding-contract** (S5–S7 / T4–T6 / U5–U7 / V7–V8 / W8–W10 / X5–X7 / Y4–Y7; 55 numbered entries in total).
- **Binding rename**: `bindings/single-agent` → `bindings/standalone-agent` (three shapes: agentteams / standalone-agent / coding-cli).

### Changed

- Loop protocol phases ↔ Loop CRD `status.state` mapping (`10-LOOP §2.1`); the 9 task runtime states aligned with the upstream task contract.
- Capability declarations now use coverage levels (full/partial/declared-degraded); L1/L2/L3 reserved for reliability layering.
- Repository cleanup: internal round/date/version notes and PR progress tables removed; README tree corrected.

### Engineering

- Compiler: optional `context_tier` (S/M/L) in `team.json`; the Budget stage gains a resident-token gate (`token_estimate` = CJK chars + non-CJK / 4; fail when a tier is declared and the cap is exceeded, report-only otherwise); new `golden-tests/tests/test_tier_gate.py`.
- Binding compliance state machine: `bindings/*/compliance.json` (machine-readable coverage levels + gaps) + `make compliance`; two-tier status `compliant` / `reference` (all three bindings are currently reference).
- Evidence register: `docs/EVIDENCE.md` (`[E#]` external citations / internal observations) + `make evidence`.
- Appendix moved: `bindings/reference-mappings.md` (cross-binding non-normative appendix).

### Fixed

- Invariant count 46→55; broken link; `spawn context_refs` cap 4/6/8 (including the mandatory set).

## [1.0.0] - 2026-10-20

### Added

- **Protocol layer v1.0 frozen**: 13 bilingual clauses under `core/protocol/` (00-OVERVIEW ~ 12-REDLINES), 8 CAP-* capabilities + 55 invariants (34 capability invariants + 21 implementation sub-items/supplements).
- **Core documents**: `core/binding-contract.md` (binding contract), `security.md` (threat model + mechanism matrix + 5 scenarios), `cost-model-tiering.md` (three cost tiers), `production-harden.md` (4 production-hardening patches), `calibration/token-shadow-calibration.md`.
- **JSON Schemas ×11**: team / spec / task_meta / decision_log / contract / contract_snapshot / handoff / loop_spec / scorecard / signal_event / aggregation_result.
- **Deterministic scripts ×9** (`core/scripts/`): validate-decision-log / detect-conflict / contract-revalidate / attention-stall / verification-mismatch-window / saga-compensate / consistency-check / aggregate-vote / timer-derive.
- **Invariant documents ×4 bilingual**: attention-state / decision-state / loop-state / task-transitions.
- **Compiler**: 6-stage zero-LLM pipeline (Validate → Assemble → Budget → Render → SelfCheck → Provenance), `validate` / `compile` subcommands.
- **Templates ×43 bilingual**: skeleton ×4 / fragments ×12 / domain ×21 / industry ×6, registry `templates/INDEX.yaml` with three-level provenance discipline (production / reference / llm).
- **Reference bindings ×3**: `bindings/agentteams` (with mapping-table / skill-fragments / cron-spec / deployment-guide / s3-storage body docs), `bindings/standalone-agent` (bare standalone-agent runtimes such as QwenPaw), `bindings/coding-cli` (coding-CLI runtimes such as Claude Code / QwenCode / OpenCode).
- **golden-tests**: 35-clause production baseline (`PRODUCTION-BASELINE.md`) + 13 compile gates + 83 script assertions + assertion-coverage record (`ASSERTION-COVERAGE.md`).
- **CI**: GitHub Actions three jobs (golden / bilingual completeness / sensitive scrub) + `requirements.txt` + `Makefile` + SECURITY / VERSION.

### Changed

- **Binding layer reorganised by architecture shape**: `bindings/agentteams` (AgentTeams reference binding, runtime-agnostic) / `bindings/standalone-agent` (standalone-agent runtimes: QwenPaw / OpenClaw / Hermes…) / `bindings/coding-cli` (coding CLIs: Claude Code / QwenCode / OpenCode…); product differences become matrix rows. State-directory paths corrected to `.qwenpaw/workspaces/` (qwenpaw >= 2.1; `.copaw` was the legacy copaw runtime).

- Binding/protocol layer separation finalized: runtime-specific names are allowed only under `bindings/`.
- The compiler does not implement a `binding_profile` parameter (downgraded: binding differences are carried by `bindings/` docs + runtime-side fragment injection).

### Known limitations

- Signal emission (SIG-*) and the Loop reconciler are implemented on the downstream runtime side; this repo defines schemas and invariants only.
- Some golden assertions depend on the runtime event surface (see the Blocked list in `golden-tests/ASSERTION-COVERAGE.md`).
