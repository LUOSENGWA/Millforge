# Contract Pinning + Structured Spec

> v1.0 | Provenance: round-5 8-capability ruling (CAP-STORE/CAP-STATE) + B-3/C-2/B-9 patches (round 3)
> Contract = the **observable part of a spec that is binding on downstream** (interface/format/acceptance/locked decisions), pinned in the shared store as a content-addressed artifact.

## 1. Contract Artifact

- location: CAP-STORE path contract `contracts/<contract-id>/<semver>.contract.json`
- fingerprint format: `contract:<semver>:<sha256-8>` (computed and returned by CAP-STORE at write time; **never self-declared**)
- **dual confirmation (S3)**: acceptance requires **one independent confirmer each from provider and consumer**, explicitly recorded (CAP-ROSTER Z1 weight=role)
- **B-9 contract owner independence**: the contract owner must not be the consumer implementer themselves; fallback = the parent orchestrator or a temporary spawn as independent confirmer; when unavoidable, explicitly tag `contract_owner_is_implementer: true` + critic re-review mandatory

## 2. Structured Spec (mandatory fields when NMH locks)

task spec / loop spec must contain:

| Field | Description |
|------|------|
| `goal` | one-sentence goal (not a process description) |
| `acceptance` | **structured acceptance_criteria** (each {id, check method, pass criteria}) — natural-language acceptance is the zone the C-3 consistency check cannot judge |
| `out_of_scope` | explicit exclusions (anti scope drift) |
| `decision_class` | R1-R6 (filled by the leader, human-locked; §03-5 misclassification handling) |
| `contract_ref` | the involved contract pins (`ref + fingerprint`, may be multiple) |
| `critical_delivery` | bool (one of the multi-critic voting enablement conditions, §05-7) |

## 3. Contract Pinning Rules (B-3)

- **pin = exact-semver + fingerprint**: at dispatch, record `contract_ref` and `pinned_fingerprint`
- a contract change during execution → **contract-revalidate judgment** (`core/scripts/contract-revalidate.sh`):
  - `none` → accept
  - `minor` → **in-flight task = re-verify, not rework** (rerun acceptance against the new contract; do not redo)
  - `major` → **rework required**
- **C-2 same-line constraint**: provider/consumer contract fingerprints must be on the same semver line (same major number), otherwise treat as at least major

## 4. Contract Snapshot (C-2)

- **an R6 attention answer must carry a contract_snapshot**: `{task_id, contract_ref, pinned_fingerprint, checked_at}`
- before a later spawn inherits the answer, verify the snapshot: fingerprint matches + within validity (window declared by the binding layer, default 72h)
- **fingerprint mismatch → cross-version re-verification** (the answer is not auto-invalidated, but the consistency check + acceptance must be rerun under the new contract)
- the snapshot is written to CAP-STATE (task meta); it does not depend on message retention

## 5. Relation to decision_log

- a `decision_log` entry with `contract_touch=true` = the entry touches the contract surface → truncation protection (§03-2) + any contract change triggers re-verification of it
- contract-surface decisions (R1/R5-locked interfaces/formats) = the authoritative source of "constraints & dependencies" in a handoff

## 6. Deterministic Implementation (P4/P5)

| Check | Script | Layer |
|------|------|------|
| semver classification + re-verify trigger | `core/scripts/contract-revalidate.sh` | L2 |
| fingerprint verification (re-read and compare before merge) | CAP-STORE `fingerprint(ref)` call | L1/L2 |
| contract_snapshot match | `core/scripts/consistency-check.py` pre-check | L2 |
