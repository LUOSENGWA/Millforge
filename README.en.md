# Millforge — A Compiler for Multi-Agent Team Protocols

> Compiles a production-validated agent-team collaboration protocol into directly deployable team identity files (SOUL + protocol fragments + domain specs).
> Frozen protocol, open templates, deterministic compiler — change the requirement by changing parameters, never by editing files.

**[中文 README](README.md)** ｜ License: Apache-2.0 ｜ Protocol version: v1.0 (frozen baseline)

---

## Why Millforge

The behavioral quality of a multi-agent team (one coordinator + leaders/workers/critics) depends less on how strong the models are than on whether the **collaboration protocol** is enforced. Failure patterns that recur in practice:

- An agent says "done" without having called the tool — **saying ≠ doing**
- The verifier is the producer — **self-review**
- Context overflow in long sessions, group-history noise polluting decisions, cross-team knowledge lost in group chat — **attention scarcity is the core system constraint**
- Protocol written into SOUL.md, hand-edited, then drifted — **documentation is not reproducible**

Millforge's answer: **frozen protocol layer + parameterized instances + compiled output**. Protocol clauses are frozen once (eight rounds of review); team differences are expressed entirely as `team.json` instance parameters (mission/roles/domains/budgets/switches); the compiler deterministically emits the full deployment tree. Same input, same output — drift goes to zero.

## Repository Layout

```
millforge/
├── core/
│   ├── protocol/        # protocol layer v1.0 (13 documents, frozen baseline)
│   ├── invariants/      # state-machine invariants (4: task/decision/loop/attention)
│   ├── schemas/         # JSON Schema ×11 (team/spec/task_meta/decision_log/…)
│   ├── scripts/         # deterministic scripts ×9 (voting/timeout/conflict/consistency…)
│   ├── binding-contract.md    # 8-capability contract + binding legality
│   ├── security.md      # threat model + mechanism matrix
│   ├── cost-model-tiering.md  # three human-touch tiers
│   ├── production-harden.md   # production hardening
│   └── calibration/     # token shadow-count calibration
├── compiler/            # compiler (Python, zero LLM, 6-stage pipeline) + profiles/
├── templates/           # template library (43 files, all bilingual: X.md + X.en.md)
│   ├── skeleton/        #   role skeletons ×4 (coordinator/leader/worker/critic)
│   ├── fragments/       #   protocol fragments ×12 (NMH/NMA/dual-channel/fuse/contract/governance/loop/signal/handoff…)
│   ├── industry/        #   industry templates ×6 (software/embedded/data/content/business/custom)
│   ├── domain/          #   domain fragments ×21 (web/mcu/data/market/office…)
│   └── INDEX.yaml       #   fragment registry
├── bindings/            # runtime bindings (agentteams reference / standalone-agent / coding-cli)
├── migration/           # migrating existing teams (scaffold-team.py + MIGRATION-CHECKLIST)
├── golden-tests/        # deterministic regression (T1–T10 gates / 13 cases / 83 script assertions)
└── docs/                # binding guide (adding-a-binding) + provenance/ (verbatim-inheritance source archives)
```

**Three binding shapes**:

| Shape | Directory | Applies to | Capability coverage |
|-------|-----------|-----------|---------------------|
| team platform | `bindings/agentteams/` | multi-team / cross-team handoff / multi-human isolation | 8/8 (CAP-NOTIFY partial) |
| standalone agent runtime | `bindings/standalone-agent/` | single host, multiple agent instances, no orchestration layer | 8/8 (CAP-NOTIFY partial) |
| coding-CLI execution backend | `bindings/coding-cli/` | execution backend; the parent provides state-class capabilities | 4/8 (declared-degraded) |

## Quick Start

```bash
# deps: python3 + jsonschema + pyyaml (declared)
pip install -r requirements.txt   # or `make deps`; then `make test` for all gates

# 1. write your team instance (or adapt a reference from golden-tests/fixtures/:
#    example-biz-team.json = single_user, bizmarket-team.json = multi_user)
cat > my-team.json <<'EOF'
{ "name": "my-team", "mode": "multi_user", "lang": "zh",
  "template": "software",
  "charter": { "mission": "one-sentence mission", "scope": ["…"], "non_goals": ["…"] },
  "roles": [
    { "id": "my-lead", "kind": "leader", "profile": "…", "domains": [], "skills": [], "budget": 250, "spawn": false },
    { "id": "my-dev",  "kind": "worker", "profile": "…", "domains": ["web-frontend"], "skills": ["web-frontend"], "budget": 150, "spawn": true },
    { "id": "my-critic", "kind": "critic", "profile": "…", "domains": ["test-qa"], "skills": ["test-qa"], "budget": 150, "spawn": false }
  ],
  "protocol": { "nmh": true, "nma": true, "five_clauses": true, "attention": true },
  "roster": [ { "id": "human-owner", "role": "accountable", "weight": 2.0 } ]
}
EOF

# 2. validate + compile
python3 compiler/millforge-compile.py validate my-team.json
python3 compiler/millforge-compile.py compile my-team.json --out out/my-team
```

Output `out/my-team/`: one `.soul.md` per role (identity file, under a hard line budget) + `fragments/` (full protocol text, loaded on trigger) + `spawn-specs/` (domain specs injected into spawns). Deployment: see the README of your binding.

## Bilingual Install (中文 / English)

**Every template ships as a full Chinese + English file pair** (`X.md` Chinese + `X.en.md` English, 43/43 coverage; the 13 protocol documents and 4 invariants are bilingual as well). Install language is an **instance parameter**, not a re-translation:

- **Chinese install**: set `"lang": "zh"` in team.json (the default)
- **English install**: set `"lang": "en"` in team.json
- CLI override: `--lang en` (takes precedence over team.json)

With `lang=en`, the compiler takes the `.en.md` twin of every template and emits an all-English tree (SOUL + fragments + spawn-specs). **Bilingual completeness is a hard gate**: a template missing its `.en.md` twin fails the build (no bilingual drift).

Two install entry points (after deployment): Chinese `… + lang=zh` ｜ English `… + lang=en`.

## Quality Gates

| Gate | What it does |
|------|------|
| Compiler 6 stages | Validate → Assemble → Budget (hard line gate; over = fail, never truncate) → Render → SelfCheck (zero residue / scrub vocabulary / pointer integrity) → Provenance (template version + fragment sha256 + instance fingerprint) |
| Golden regression | two compiles of the same input are byte-identical; zero leakage of production-specific names; every trigger pointer reachable |
| **Frozen baseline (T9)** | template/fragment/compiler change → output diffed against the frozen baseline; any drift requires an explicit re-freeze + human review (zero silent protocol regression) |
| **Production traceability (T10)** | production baseline (5 SOULs, anonymized) + clause mapping table: every production protocol clause must map to a v1.0 landing point; a missing mapping = protocol content lost in upgrade |

**Scrub discipline**: the core layer admits only CAP-* capability numbers + generic terms; runtime-specific API names (each runtime's subagent/storage/timer mechanisms) live in the binding layer. The open-source baseline carries no deployment environment names, human MXIDs, or internal incident numbers.

## Protocol Layer v1.0 (13 Documents)

00 Overview / 01 Primitives / 02 Modes (single_user/multi_user) / 03 Decision Classes (R1-R6) / 04 NMH (human↔agent interrogation & locking) / 05 NMA (peer review) / 06 Lifecycle (dispatch triad / TASK_COMPLETED / failure SOP) / 07 Cross-team Handoff / 08 Contract Pinning / 09 Governance (voting/ruling/fuse) / 10 Loop Primitive / 11 Signal Primitive / 12 Redlines

Core design stance: **verifier ≠ declarer**, **the file is the contract**, **state externalized** (messages may be lost, state must not), **attention budget** (three-layer loading + hard line budgets; capacity ≠ attention).

## Philosophy & Second-Order Generation

`PHILOSOPHY.md` is the full design philosophy — **copy it in full + describe your team's situation, feed it to any LLM, and it can generate your `team.json` or a custom industry template** (the second fallback channel when the template library does not cover your case).

## Contributing

**Not open yet** (the repo is in its protocol stabilization phase). The contribution process will be enabled once the protocol layer stabilizes: protocol-layer changes go through the full review process; template changes follow the three-tier source discipline (production/reference/llm).

## Acknowledgments

Mechanism provenance (including verbatim-inherited external designs) in [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).

## License

Apache-2.0 (see [LICENSE](LICENSE)).
