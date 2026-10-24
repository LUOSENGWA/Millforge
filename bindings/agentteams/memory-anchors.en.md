# Memory Anchors — AgentTeams Binding Extension

> Status: reference extension (not core). Applies to: `bindings/agentteams/`.
> Upstream RFC: `agentscope-ai/AgentTeams#1412` (scoped, runtime-agnostic memory).
> Depends on: `core/protocol/03-DECISIONS.md` (decision_log / B-1/B-2), `04-NMH §7` (sources), `09-GOVERNANCE.md` (R1–R6/R5/C-3), `core/scripts/` (9 scripts).
> **This document adds no primitive, changes no core schema, and changes no core script.**

## 1. Scope: three anchors

| anchor | prefix | owner | access surface |
|---|---|---|---|
| human | `humans/<human>/` | one person | the person via controller API; the serving agent writes via API; **no agent is granted `humans/*`** |
| team | `teams/<team>/` | one Team | team members (`teams/<team>/*` already in the worker policy) |
| agent | `agents/<agent>/` | one agent identity | that agent only; no cross-agent reads |

No global `shared/*` memory: `shared/*` is readable/writable by all workers, so personal/team facts there would break isolation.

## 2. Fact entry = decision_log superset

One fact = one `decision_log` object (1 entry), reusing the core schema; the binding adds 6 extension fields:

```json
{
  "schema_version": "1.0",
  "task_id": "teams/team-a/api-base-url",
  "spawn_id": "9f3c1e7a-<random-uuid>",
  "entries": [{
    "id": "f-0007",
    "decision": "team API base URL = https://api.example.com/api",
    "rationale": "matches deploy manifest; two members cross-checked",
    "decision_class": "R1",
    "affected_artifacts": ["teams/team-a/api-base-url"],
    "contract_touch": true,
    "type": "fact.config",
    "field": "value",
    "value": "https://api.example.com/api",
    "assumptions": [{"key": "dns-internal", "holds": true}],
    "decided_at": "2026-10-24T11:20",

    "actor": "leader",
    "scope": "team",
    "source": "CAP-STORE:ref=deploy/manifests/team-a.yaml#L42;sha256_8=ab12cd34",
    "checked_at": "2026-10-24T11:18",
    "supersedes": "f-0006",
    "promoted_from": "agents/worker-a/digest/deploy-note.md"
  }]
}
```

| field | origin | discipline |
|---|---|---|
| `task_id` | core | `"<scope>/<key>"`; the key is the fact key (not a task id) |
| `spawn_id` | core | unpredictable random UUID per write (S2 anti-forgery), not the agent name |
| `decision` / `rationale` | core | the fact statement / why |
| `decision_class` | core | R1–R6; determines the aggregation rule (§4) |
| `affected_artifacts` | core | `["<scope>/<key>"]`; `detect-conflict.py` uses it for shared-surface detection |
| `type` | core | closed enum (type registry) with a semantic dimension; no runtime invention |
| `field` / `value` | core | used by conflict detection; `value` compared with `detect-conflict.py`'s `norm()` |
| `assumptions` | core | `[{key, holds}]`; opposite holds on the same key = assumption-conflict |
| `contract_touch` | core | true → truncation protection + `contract-revalidate.sh` |
| `actor` | binding | the actual writer (human/agent id) |
| `scope` | binding | `human` / `team` / `agent` |
| `source` | binding | resolvable source (file+line / CAP-STORE ref+fingerprint / external doc / human quote) |
| `checked_at` | binding | when the source was last verified |
| `supersedes` | binding | previous entry id; old entries are never deleted |
| `promoted_from` | binding | the agent-private fact/digest this was promoted from |

**Source red line**: no resolvable `source` → the entry cannot become current (`04-NMH §7` fail-closed); "I remember / I know" is not a source.

**Source grammar**: `file:<path>#L<line>` / `cap-store:ref=<ref>;sha256_8=<hex>` / `external:<url>` / `human:<quote-ref>`; non-empty with one of these prefixes; secrets use `secret:<ref>`, never a value.

**Key discipline**: `task_id` must equal `affected_artifacts[0]` (the same fact key); `detect-conflict.py` keys on `affected_artifacts`, so a mismatch yields a false `shared-surface` (verified in V17a).

**Stable identity**: anchor keys use stable IDs (human = Matrix user_id / team = CRD UID / agent = agent id), not display names; rename = R1 migration (copy to the new prefix + keep the old prefix read-only), never a silent orphan.

## 3. Storage: chained objects + derived Markdown

```
teams/<team>/facts/<key>/
  0001.json                 # decision_log (1 entry), immutable
  0002.json                 # next write, new object (CAP-STORE T3)
  latest.json               # pointer {seq, ref, sha256_8}
  current.md                # derived read model (human + BM25)
  conflict-candidates.json  # written by detect-conflict.py on conflict
  record.jsonl              # append-only audit (when write-decision-record.sh lands)

humans/<human>/facts/<key>/…    # same shape; writes only via controller API
agents/<agent>/facts/<key>/…    # same shape; private to the agent
```

- **one write = one object** → satisfies `entries ≤ 10` without stuffing history.
- `latest.json` is updated atomically (tmp+rename) **only after sync acknowledgement** (F-1); readers see the old pointer until then.
- `current.md` is generated by `fact-project.py` (binding helper) from the latest entry; **JSON is authoritative, Markdown is the read model**. Never hand-edit `current.md`.
- Retrieval: team `current.md` → member `digest/team/facts/<key>.md` (reuses the validated recursive `digest/team/` index); human → serving agent `digest/human/facts/`; agent → `digest/facts/`.
- IAM unchanged: workers already have `teams/<team>/*`; `humans/*` remains API-only (no agent grant).

**Concurrent writes (multiple writers, same key)**:
- Object name = `facts/<key>/<ULID>.json` (ULID monotonic, collision-free), **not an auto-increment seq**.
- Write flow: write object → sync acknowledgement (F-1) → read `latest.json` → if the pointer is unchanged, CAS-style update (read-modify-write with N retries) → write `current.md.tmp` + rename.
- If the pointer changed during the write → re-read the current object → re-run `detect-conflict.py` (new vs new current) → mark conflict if any, otherwise retry.
- **Objects are never overwritten**; worst case = multiple candidate objects + a conflict mark, never a silent lost update.
- After writing `latest.json`, read it back; if the pointer is not yours → treat it as a concurrent conflict and re-run `detect-conflict.py` (new vs new current); never assume you won.
- Stale write: the new entry's `decided_at` must be ≥ the current entry's; otherwise reject or route to R5.

## 4. Conflict pipeline

```
proposal (new 000N.json)
  → 1. validate-decision-log.sh <new>                 exit 0/10/11/12
  → 2. read <key>/latest.json → current object <cur>
  → 3. detect-conflict.py <cur> <new> [--type-registry <reg>]
         exit 0  no candidate → update latest + current.md + audit
         exit 20 hard-conflict (same field, different value / type dimension mismatch) → reject
         exit 21 assumption-conflict (same key, opposite holds) → reject
         exit 22 shared-surface only → Step 4 semantic confirmation (bounded classifier / human)
  → 4. on conflict: write conflict-candidates.json + conflict_state.resolved=false
  → 5. resolution = a NEW decision entry (R1–R6) carrying supersedes + rationale + assumptions; old entries retained
  → 6. final authority = human (agent arbitration only produces escalation signals)
```

**Voting state (R2/R5)**: add `meta.json` per fact key (a `task_meta.schema.json` subset: `{task_id, decision_status, attention[]}`); `aggregate-vote.sh --task-meta <key>/meta.json --decision-id <id> --rule R2|R5` is reused as-is. No `meta.json` → `wait` (never auto-pass). `meta.json` writes: one writer per decision (protocol layer) or the same optimistic retry; `votes[]` is append-only.

**Resolution rules (R1–R6):**

| class | rule | team-fact owner |
|---|---|---|
| R1 irreversible/external | owner single-point; dissent recorded; owner absent → human | Leader |
| R2 resource | weighted majority (`aggregate-vote.sh`; tie → escalate) | Leader + members |
| R3 style/quality | single writer decides; NMA rework | writer |
| R4 reversible detail | auto-pass, log | writer |
| R5 reopen locked | explicit reopen (new evidence + affected acceptance; original locker ×2; timeout 24h/4h → weight 1.0, not default-yes; old lock retained marked overridden) | original locker / Leader |
| R6 spec ambiguity | route accountable; `consistency-check.py` before write-back; no auto-release | accountable / human |

**Hard rules**: no auto-merge (`00-OVERVIEW §5`); no vote ≠ yes; tie → escalate; final human (`09-GOVERNANCE §7`); old value never deleted (`supersedes` + audit chain); optional pre-write gate: `conflict_state.resolved=false` → reject new writes until resolved (analog of PD-2).

## 5. Roles and jurisdiction: `leader ≡ arbitrator`

`core/protocol/01-PRIMITIVES.md` already defines leader and arbitrator as the same orchestrator role kind, differing only in jurisdiction and existence:

| scope | fact anchor | arbiter | existence |
|---|---|---|---|
| team | `teams/<team>/facts/` | **Leader** | mandatory |
| cluster/cross-team/ops | cluster-level facts | **arbitrator** | single_user only; Manager is the binding |
| human | `humans/<human>/facts/` | the human (writes via API; serving agent proxies) | independent of Manager |
| agent | `agents/<agent>/facts/` | the agent | not cross-agent |

One scope, one arbiter; no overlap; final authority = human.

## 6. Promotion and provenance

- **Promotion is an explicit write**, not a blanket mirror: agent-private fact/digest → `teams/<team>/facts/<key>/000N.json`, with `promoted_from` + `source` + `rationale` + `checked_at`.
- The team fact area does **not** receive bulk `memory/`/`digest/` copies; only promoted entries enter.
- Readers verify against `source` before acting (`04-NMH §7`).

## 7. Lifecycle

| object | lifecycle | cleanup |
|---|---|---|
| task-scoped decision_log | per task | terminal state first (PD-3), then cron/session cleanup |
| durable team fact | cross-task/member | **never auto-delete**; GC only by R1/human; old entries retained |
| human fact | follows the human | only the human may delete |
| agent-private fact | follows the agent | agent rename/recreate does not carry it (by design) |
| `current.md` | derived | rebuildable; not separately backed up |
| `record.jsonl` | append-only | never cleaned (audit) |

Reclassification: B-10 `decision_class_v2` new record, original not overwritten. `contract_touch=true` → `contract-revalidate.sh`; major → human.

## 8. Capability and degradation

- Deterministic scripts run under **CAP-EXEC**; if a runtime cannot run them, the binding declares `supported: false` and falls back to "protocol trigger + manual fallback" (same as the `[NO-CARRIER]` rule).
- If a memory backend lacks a capability (e.g. vector search), the contract reports `supported: false` and degrades (e.g. to BM25); no hard error.
- Engine replacement: the JSON chain is the source of truth; any engine indexes `current.md`; no engine's internal layout becomes the contract.

## 9. Explicitly unchanged

| item | change? | reason |
|---|---|---|
| 15 primitives | no | fact is a projection of decision_log, not a 16th primitive |
| `decision_log.schema.json` | no | binding uses an `allOf` superset for the 6 extension fields |
| `detect-conflict.py` / `validate-decision-log.sh` | no | inputs remain decision_log objects; fields match |
| `aggregate-vote.sh` / `consistency-check.py` | no | R2/R5 and R6 reused as-is |
| core protocol | no | durable-fact semantics live in the binding; a future core promotion is a separate minor |
| `shared/*` | no | global shared memory would break isolation |

## 10. Validation

**Script-level (no container):**

| # | assertion | command | expected |
|---|---|---|---|
| a1 | valid fact entry | `validate-decision-log.sh new.json --task-id ... --spawn-id ...` | exit 0 |
| a2 | same field, different value | `detect-conflict.py cur.json new.json` | exit 20, `hard-conflict` |
| a3 | same key, opposite assumption | same | exit 21, `assumption-conflict` |
| a4 | shared surface only | same | exit 22, `shared-surface` |
| a5 | no conflict | same | exit 0 |

**Two-runtime (T2, real containers):** one team with a QwenPaw worker + an OpenClaw worker: A's `agents/A/` private is not retrievable by B; a team fact is retrievable by both; `humans/<h>/` is reachable only via the human's API; switching A's runtime preserves A's memory.

**Real conflict (T2):** two writers on the same key → 20 → Leader/human writes the resolution entry (`supersedes`) → old entries retained → `current.md` updated.

## 11. Dependencies

| dependency | status | impact |
|---|---|---|
| `core/scripts/write-decision-record.sh` | planned, not implemented | `record.jsonl` audit unavailable; use immutable chain + `latest.json` until then |
| `fact-project.py` (JSON → `current.md`) | to be added (binding helper, ~100 lines) | read model generation |
| type registry (`type_registry.json`) | binding-deployed | closed enum; new types require critic review |
| retention policy | default permanent | compaction only moves old `current.md` versions, never the JSON chain |

## 12. Knowledge-graph projection (engine-pluggable)

**Current state**: the dashboard's `assembleGraph` builds a graph from `MEMORY.md` + `memory/**` + `digest/**` Markdown and `[[wikilink]]`s; the data is read through the controller's Docker proxy from the **container workspace** → tied to the QwenPaw layout. The graph is not an independent engine; it is a derived projection of memory files.

**Goal**: graph = a derived projection of canonical memory + fact chain; contract-based; engine-swappable; any runtime that writes the canonical layout gets a graph.

**Three independent boundaries (runtime / memory engine / knowledge graph)**:
- A runtime (QwenPaw/OpenClaw/Hermes/DSH) only calls the memory contract (capture/recall/write/promote/resolve/capabilities); it **does not touch the graph**.
- A memory engine (ReMe/new engine/PowerContext) only implements the memory backend contract and persists to canonical; optional `graph_native`.
- The graph reads only canonical + the fact chain; it **does not depend on the runtime or on a specific engine**; swapping either layer changes only its adapter.
- One line: runtime swap / engine swap / graph-backend swap are independent; the canonical layout + contract stay unchanged.

```
graph.snapshot(scope, {root, depth, budget}) -> {nodes, edges, meta}
graph.neighbors(node_id, {direction, depth}) -> {nodes, edges}
graph.search(query, {scope, limit})          -> {nodes}
graph.path(from, to)                          -> {nodes, edges}   # optional
graph.timeline(node_id)                       -> {edges}          # optional
graph.capabilities()                          -> {snapshot, neighbors, search, path, timeline, vector}
```

- **Node**: `{id, kind: memory_file | fact_key | virtual | unresolved, label, scope, path, props}`.
- **Node id namespaces**: file = path; fact = `fact:<scope>/<key>`; virtual = `virtual:<bucket>`; unresolved = `unresolved:<raw>` (prevents a fact key from colliding with a file path).
- **Edge**: `{s, t, kind: structural | wikilink | fact | provenance | temporal, props}`.
  - `fact`: fact_key → target entity; `provenance`: fact_key → `source`/`promoted_from`; `temporal`: new fact_key → superseded fact_key.
- **Source**: canonical object storage (`agents/`, `teams/`, `humans/`) + fact chain; the graph is derived, **not the source of truth**.
- **Default adapter `file-graph`**: a pure parser (Markdown + wikilink + fact chain), no ReMe, no container FS, no new service; the implementation location is not mandated (controller library or an equivalent dashboard pure function), but the **data source must be object storage**.
- **Exposure**: the memory module's MCP surface calls the controller's read-only graph model; the default `file-graph` runs in the controller.
- **Memory engine adapters**: ReMe / a new engine / PowerContext; they implement the memory backend contract.
- **Graph backend adapters**: `file-graph` (default), `reme-file-graph` (current), `neo4j`, `nebulagraph`, `powercontext-graph`; ingest/rebuild from canonical.
- These are different layers: **a memory-engine swap is not a graph-backend swap**.
- **Idempotent ingest**: keyed by `(kind, id, sha256_8)`; full rebuild from canonical.
- **Runtime neutrality**: the graph API reads object storage, not the container FS; the Docker proxy is a QwenPaw fallback only.
- **Scope filtering**: team graph = `teams/<team>/` only (no `shared/*` — `shared/*` is not memory); human graph = `humans/<human>/` via that human's API only; agent graph = `agents/<agent>/`; no cross-scope leak.
- **Per-scope roots**: agent = `agents/<id>/{memory,digest,facts}`; team = `teams/<id>/{memory-digest,facts}`; human = `humans/<id>/{memory,digest,facts}`; the adapter picks the root per scope and does not assume a uniform `memory/digest` layout.
- **Capability degradation**: missing `path`/`timeline`/`vector` → `supported:false`; UI hides/degrades; no hard error.

**Migration**: Phase 1 keeps the Docker-proxy graph and adds a read-only `file-graph` path (equivalence assertion V18a on the same fixture); Phase 2 switches the dashboard to `graph.snapshot`, Docker proxy becomes fallback; Phase 3 optional graph engines.

## 13. Privacy and lifecycle

- **Secrets red line**: `value` / `source` must not contain credentials, tokens, private keys, or passwords; store a secret ref only (e.g. `secret://vault/...`); public examples use `example.com` / placeholder IDs.
- **Human deletion**: a human may delete their own facts via the API: write an `op=delete` R1 entry (tombstone) + delete the content object; the audit keeps only the deletion event (`decision_id/actor/timestamp`), not the content; teams/agents may not delete on the human's behalf. Tombstone = `humans/<human>/facts/<key>/deleted.json` (only `{decision_id, actor, timestamp, reason}`).
- **Retention**: durable facts default to permanent; after N months they may be compacted to a snapshot + index (the JSON chain is not deleted); GC only by R1/human.
- **Team/agent rename**: anchor keys use stable IDs (team CRD UID / agent id); display names are metadata; rename = R1 migration (copy to the new prefix + keep the old prefix read-only).

## 14. Additional validation

| # | Assertion | Expected |
|---|---|---|
| V18a | `file-graph` vs the current dashboard `assembleGraph` on the same fixture | identical memory-file subgraph (structural + wikilink); fact/provenance/temporal edges are additive and asserted separately |
| V18b | **memory-engine swap** (ReMe → new engine, same runtime) | identical `graph.snapshot` |
| V18c | **runtime swap** (QwenPaw → OpenClaw, same engine) | identical `graph.snapshot`; no Docker-proxy dependency |
| V18d | **graph-backend swap** (file-graph → Neo4j / mock) | identical `graph.snapshot` |
| V18e | team graph excludes `humans/*`; human graph is self-only | zero leak |
| V19 | two concurrent writers on the same key (optimistic retry) | no lost update; conflict marked |
