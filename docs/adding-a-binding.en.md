# How to Add a Runtime Binding

> A binding is the mapping layer between the Millforge core and one runtime. The core recognises only **CAP-*** capability ids; the binding explains "which mechanism of this runtime satisfies it".

## 1. Pick a shape first (one of three)

| Shape | Directory | Fits | Product examples |
|---|---|---|---|
| **orchestrated** | `bindings/agentteams/` | orchestration platforms with a control plane + worker pool | AgentTeams (any worker runtime) |
| **standalone-agent** | `bindings/standalone-agent/` | standalone-agent runtimes without an orchestration layer | QwenPaw / OpenClaw / Hermes |
| **coding-cli** | `bindings/coding-cli/` | one-shot coding CLIs | Claude Code / QwenCode / OpenCode / Codex CLI |

> A shape is an **architecture shape**; product differences become **matrix rows** — never open a directory per product.

## 2. Write three files (each with a bilingual twin)

| File | Content |
|---|---|
| `mapping-table.md` | per-capability mapping for the 8 CAPs (carrier + status + risks); product matrix (one row per product); any unmet hard gate stated explicitly with consequences |
| `skill-fragments.md` | how spawn / scripts / the review chain land on this runtime; reuse the deterministic scripts in `core/scripts/` where possible |
| `deployment-guide.md` | deployment form, config paths, failure sequences and recovery (write from verifiable facts; use `TBD` rather than inventing) |

## 3. Compliance declaration (mandatory)

- Are all 8 capabilities satisfied? **Any unmet hard gate must be declared explicitly** (e.g. CAP-SPAWN X1 is unmet for coding CLIs).
- Wording: `compliant` = 8/8 with all hard gates passed; otherwise `reference` (usable as a reference, not compliant).
- Put the overall verdict in the header of `mapping-table.md` (e.g. "7.5/8, reference, X4 best-effort").

## 4. Acceptance

```bash
make test                                   # golden 13 + 83 must be green
# bilingual completeness: every new md needs an .en twin
# sensitive info: no credentials / private addresses / personal markers
```

## 5. Boundaries (iron rules)

- The core layer (`core/` and `templates/`) **must not** contain that runtime's specific names; they appear only under `bindings/`.
- Binding docs **do not change protocol semantics**: the core says "what must happen", the binding says "how it happens here"; on conflict the core wins and the difference is recorded.
- Adding a product = add one matrix row inside an existing shape directory + a difference note; **never create a new shape directory**.
