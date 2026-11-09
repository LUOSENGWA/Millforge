# Acknowledgments & Mechanism Provenance

Millforge stands on the shoulders of a number of open-source projects and public protocols. This file is organised as: projects and communities → verbatim inheritance → adaptations → references → third-party dependencies → brand.

## 1. Referenced Projects and Papers

### 1.1 Projects

| Project | What we drew on |
|------|------|
| [`grill-me`](https://github.com/mattpocock/skills/blob/main/docs/productivity/grill-me.md) / [`grill-with-docs`](https://github.com/mattpocock/skills/blob/main/docs/engineering/grill-with-docs.md) (Matt Pocock's skills repository) | The mechanism source of NMH (verbatim inheritance; point-by-point mapping in §2). Introduction: <https://www.aihero.dev/skills-grill-me> |
| [`dsh-superagent-prototype`](https://github.com/deepseek-ai/dsh-superagent-prototype) (deepseek-ai, MIT) | Task DAG + CAS revision, a closed set of approval outcomes, latest-only catch-up scheduling, and the principle of judging every design by the human attention it costs (*take as little human attention as possible, and give as much value as possible*) |

### 1.2 Papers

| Paper | What it supports | Source |
|------|------|------|
| Liu et al., *Lost in the Middle: How Language Models Use Long Contexts* | U-shaped long-context attention (strong at the ends, weaker in the middle) → identity-file line budgets and three-layer loading | arXiv:2307.03172 |
| *Beyond Calibration: Temporal LLM Confidence Assessment Across Languages and Local Settings* | Hallucinated answers keep high confidence after generation → declare-verify binding | arXiv:2610.27702 |
| *CHARM: Character Hallucination for Multicultural Role Play Benchmark* | Models may recognise an out-of-scope query yet still answer (a compliance failure, not an awareness failure) → declare-verify binding | arXiv:2609.01352 |

> These three are the external citations registered in `docs/EVIDENCE.md`.

## 2. Verbatim (word-for-word inheritance, original text verifiable)

**NMH (collaborative exploration / interrogation & locking protocol) ← `grill-me` / `grill-with-docs` from Matt Pocock's skills repository**

Inheritance points mapped one by one (originals archived at [`docs/provenance/grill/`](docs/provenance/grill/), preserved as-is):

| Millforge NMH mechanism | Source (original wording) |
|------|------|
| Branch-by-branch interrogation of the decision tree (walk the tree, resolve dependencies level by level) | grill-me: "Walk down each branch of the design tree, resolving dependencies between decisions one-by-one" |
| One question at a time (no batch bombardment) | grill-me: "Ask the questions one at a time" |
| Each question carries a recommendation (options + pick + rationale) | grill-me: "For each question, provide your recommended answer" |
| Questions answerable by context exploration are explored, not asked | grill-me: "If a question can be answered by exploring the codebase, explore the codebase instead" |
| Terminology alignment: conflicting terms called out immediately ("do you mean X or Y?") | grill-with-docs: "Challenge against the glossary … call it out immediately" |
| Fuzzy-language sharpening (overloaded terms → precise canonical term) | grill-with-docs: "Sharpen fuzzy language … propose a precise canonical term" |
| Concrete-scenario stress testing | grill-with-docs: "Discuss concrete scenarios … stress-test them with specific scenarios" |
| Write-to-disk discipline: terms/decisions written immediately, never batched at the end (the immediacy behind "the file is the contract") | grill-with-docs: "Update CONTEXT.md inline … capture them as they happen" |
| Restrained escalation of high-weight decisions (only when irreversibility + surprise + real trade-off all hold) | grill-with-docs: "Offer ADRs sparingly — Only offer … when all three are true" (Millforge's counterpart: the attention-raising bar for R1/R6) |

**Millforge extensions (not inherited; original work)**: explore/lock dual mode, the seven-question pre-lock self-check, the NMH document structure (nodes / options / human's own words / timestamps), R5 versioning (append, never overwrite), locking output as a structured spec (goal / acceptance / out_of_scope / decision_class / contract_refs), integration with the 7 closed-signal system. None of these exist in the source skills.

## 3. Adapted (mechanism borrowed, Millforged)

| Millforge mechanism | Borrowed from | Millforge transformation |
|------|------|------|
| NMA peer review (review ticket / re-review loop / escalation chain) | General engineering ticket-based peer review practice (no specific upstream; public engineering convention) | ticket triad (what is checked / command / expected) + 🟢🔵❌ evidence grading + isolation boundary (reviewer never enters the reviewed party's workspace) + multi-critic voting (≥2 model families) + B-6 deadlock defense |
| Contract Pinning (semver pinning + fingerprint) | General software dependency-management / semantic-versioning practice | contract object = the externally binding face of a spec (not a code package); dual confirmation (provider + consumer); in-flight change verdict minor=re-verify / major=rework |
| Hard line budgets (identity-file line ceiling; over = fail) | General LLM context-engineering practice (attention-budget awareness) | compile-time enforcement (Budget stage), never truncation; U-shaped attention distribution → three-layer loading |
| Failure SOP (restart → re-dispatch → escalate after 3) | General ops "backoff / escalation" thinking | hardened into a role duty (the orchestrator never does the work); attempt count and escalation path are instance parameters |

## 4. Referenced (cited during design review; text not inherited)

- **The 12 principles of distributed systems**: the methodology stress-test framework applied after every Millforge architecture decision (its principle dimensions are referenced; its text is not copied).
- **Multi-round adversarial review by an external strong model**: the review method for protocol layer v1.0 — each round an external strong model adversarially reviews the draft, and every gap is either adopted or recorded with reasons. This is Millforge's **review process** (a process contribution), not a mechanism lineage.

## 5. Third-Party Software Dependencies

| Dependency | Use | License |
|------|------|------|
| Python 3 standard library | compiler core | PSF |
| `jsonschema` | team.json schema validation | MIT/Apache-2.0 dual |
| `pyyaml` | INDEX.yaml parsing | MIT |

## 6. Brand and Visuals

- **Logo design**: Tang Yiyang / 汤逸阳 ([Tangyiyang906@gmail.com](mailto:Tangyiyang906@gmail.com))
- **Files in this repository**: `docs/assets/brand/millforge-logo.svg`, `avatar-512.png`, `social-preview-1280x640.png`

## 7. Discipline Statement

1. The repository body text (protocols / templates / docs) contains **zero sentence-level copying** of external text — the verbatim correspondences in §2 exist only at the **mechanism-pattern** level (behavioral patterns such as branch-by-branch decision-tree interrogation); Millforge's own wording is entirely rewritten under its own terminology system.
2. The sole exception: the two skill originals in `docs/provenance/grill/` are preserved as-is (verbatim inheritance requires citation; the originals must be verifiable).
3. Any new verbatim inheritance must: ① add a row to this file ② archive the original under `docs/provenance/` ③ sync a "design provenance" section in the relevant protocol document. Missing any of the three = the PR must not merge.
