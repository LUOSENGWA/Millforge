# Industry Template: Software

> T1 industry fragment · source: production (software R&D team field work)
> Applies to: worker / leader / critic

## Worker industry constraints

- **Context isolation reinforced**: repository-level tasks (clone/build/test) must be spawn-isolated — the native session only decomposes and accepts. Build output/logs never enter conversation (write to file, reference the path)
- **Git discipline**: add specific files only (`git add -A` / `add .` forbidden); `git status --short` to check the staging area before commit; single-side operation during rebase/cherry-pick
- **Verification = running**: code artifact acceptance = build passes + tests pass + key paths manually verified (every scorecard line executable)
- **Environment discrimination**: three checks for container/host/mounted paths (is the target a persistent volume / permissions / relative path resolution); docker operations start with `docker ps` + `docker exec` to verify actual state, never assume
- **Dependency versions**: pip/npm versions = the feature timeline basis (changelog first; never infer features from the version number)
- **Build artifacts**: three checks on the output path (is the container --rm / the target volume / permissions)

## Leader industry constraints

- decomposition granularity = an independently acceptable module (clear file boundary + test surface)
- cross-module tasks fix the interface contract (contract artifact) first, then dispatch in parallel
- CI/deployment tasks = R1 (human informed)

## Critic industry constraints (review perspective)

- executable verification first: grep/build/test/API call > reading code and judging
- isolation boundary: never execute inside the reviewed party's container; 🔵 items limited to API endpoints / object storage / CI status
- review dimensions: correctness (tests + logic) / boundaries (error paths) / regression (impact-surface grep) / security (injection surface / permission surface)
