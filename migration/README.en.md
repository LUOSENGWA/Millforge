# Migration Guide (B-7, Strangler Fig in three phases)

> This directory ships the tools and procedure for **migrating an existing team** onto the Millforge protocol. Principle: no big-bang rewrite — replace incrementally, strangler-fig style.

## Three phases

| Phase | What happens | Output | Exit criterion |
|---|---|---|---|
| **1. Shadow** | The existing team keeps running; `scaffold-team.py` **reverse-generates** a `team.json` skeleton from the current roles; compiled artifacts are compared only, never deployed | `team.json` (with TODO markers) + difference report | the skeleton covers every current role and duty; no unknown roles in the difference report |
| **2. Parallel** | New protocol fragments (decision_log / contract / critic isolation) run incrementally on the shadow team; critical decisions are dual-written (old flow + new protocol artifacts) | sample decision_log / contract_snapshot artifacts + an item-by-item human confirmation checklist | dual-write agreement reaches the agreed threshold; checklist fully green |
| **3. Cutover** | The old flow is retired; the new protocol becomes the only execution path; a rollback window is kept | cutover record + rollback plan | rollback window closes with no incidents |

## Scaffold generator usage

```bash
python3 migration/scaffold-team.py \
  --from <existing roles directory (containing *.soul.md)> \
  --name my-team --mode multi_user --lang zh \
  --out team.json
```

- Reads only role filenames and the first identity line to infer `id` / `kind` (coordinator / leader / worker / critic);
- Emits a **schema-valid** `team.json`; anything unknown is filled with a `TODO:` placeholder (charter goals, scope, weights, budgets);
- No network / LLM calls (deterministic, re-runnable): same input → same output.
- The result must pass the **human confirmation checklist** (`MIGRATION-CHECKLIST.md`) before phase 2.

## Boundaries

- The tool **never** modifies any running file of the existing team; it only produces new files.
- Content that cannot be inferred (human members, weights, decision classes) **must be filled by a human** — no guessing.
- Relation to the frozen baseline: a migrating team's `team.json` never enters `golden-tests/`; the frozen baseline belongs to protocol regression only.
