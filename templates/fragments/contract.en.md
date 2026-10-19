## Contract Pinning (condensed load · full text = protocol §08-CONTRACT)

**Contract object**: the observable, binding-on-downstream part of a spec (interface/format/acceptance/locked decisions) → CAP-STORE `contracts/<id>/<semver>.contract.json`; the fingerprint `contract:<semver>:<sha256-8>` is computed and returned by CAP-STORE at write time (**never self-declared**).

**Dual confirmation (S3)**: acceptance needs one independent confirmer each from provider and consumer, explicitly recorded. B-9: contract owner ≠ consumer implementer (fallback = the parent orchestrator / a temporary spawn as independent confirmer; unavoidable → tag `contract_owner_is_implementer` + mandatory critic re-review).

**Pinning rules (B-3)**: at dispatch record contract_ref + pinned_fingerprint (exact semver). A contract change mid-execution → deterministic decision (contract-revalidate):
- `none` → accept
- `minor` → **in-flight task = re-verify, not rework** (rerun acceptance against the new contract; do not redo)
- `major` → **rework required**
- C-2 same line: provider/consumer fingerprints must be on the same semver line (same major number), otherwise treat as major

**contract_snapshot (C-2, mandatory on every R6 answer)**: {task_id, contract_ref, pinned_fingerprint, checked_at} → a later spawn inherits the answer only after verification: fingerprint matches + within validity (default 72h); **mismatch = cross-version re-verification** (the answer is not auto-invalidated, but the consistency check + acceptance run again).

**decision_log linkage**: entries with `contract_touch=true` = truncation protection (a truncation containing contract entries = violation) + a contract change triggers re-verification of them.
