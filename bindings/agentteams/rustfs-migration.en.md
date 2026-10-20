# RustFS Migration (MinIO → RustFS, S3 Semantics Verification)

> Provenance: production-readiness + open-source-readiness review (round 6, 2026-10-18), finalized; adoption status = adopted. This file is the object-storage migration spec for `bindings/agentteams/`. This layer may name MinIO/RustFS (generic-terminology discipline: see the `README.md` header).

## 1. CAP-STORE T1–T3 Implementability under Pure S3 Semantics

| Invariant | Implementation under S3 semantics | Feasibility |
|---|---|---|
| **T1 content addressing** | client-side SHA-256 (an S3 ETag is not guaranteed to be a content hash; a multipart-upload ETag is a hash-of-part-hashes and cannot serve as a content fingerprint). The client computes the hash as `fingerprint`; the S3 ETag is a transport-check aid. | ✅ feasible; **key**: the fingerprint is computed by the client, never derived from the ETag |
| **T2 write confirmable** | S3 provides **strong read-after-write consistency** (a GET immediately after a successful PUT is visible); since 2024, **conditional writes** are supported (If-None-Match: * to create, If-Match: ETag to overwrite), failures returning 412 PreconditionFailed. Before `write` returns `{ref, fingerprint}`: ① PUT the object; ② after the successful PUT, verify existence and ETag via a conditional GET/HEAD; ③ return. | ✅ feasible |
| **T3 append optional** | S3 has no native append. Same-key append is unsafe under concurrency (conditional PUT serializes; hot-key throughput is bounded). **Alternative**: append-only is simulated with "new object + old-object chain" — each record writes a new object (`decisions/<task>/<seq>.json`); append returns the chain-tail ref; reads sort by seq. | ✅ feasible (chained simulation, no same-key append) |

**T3 core wording (already in CAP-STORE)**:

```
“append(path, entry) -> new_ref. Implementations may be: ① same-object
JSONL append (when the runtime supports safe concurrency); ② new-object
chained append (entry_ref = path + seq; append returns the chain tail);
③ any equivalent semantics. The core only requires read(ref) to return
all entries in append order — it does not require a single physical
object.”
```

## 2. CAS Positioning (CAP-STATE vs CAP-STORE)

- S3 conditional writes (If-None-Match / If-Match) are **object-level**, not key-value-level CAS.
- **CAP-STATE must not simulate CAS via object-store conditional PUT**, unless the same-key concurrency bound is acceptable. State needing "atomically update multiple fields" is the responsibility of the CAP-STATE implementation (local file lock or dedicated KV); object storage serves CAP-STORE only.

## 3. T2 Execution Detail (Sync-Layer Confirmation)

```
“Where the write path crosses a sync layer (workspace ↔ object-store
asynchronous sync), write must confirm — before returning — that the
sync layer has persisted the object to the object store (the sync
layer's uploaded/committed receipt). An unconfirmed write must not
return {ref, fingerprint}; callers must not consume an unconfirmed ref.
The sync layer's implementation (push_loop, mirror, rsync, etc.) is a
binding parameter, but 'return only after confirmation' is T2's
mandatory semantics.”
```

Ownership: T2 semantics go into CAP-STORE; the concrete confirmation mechanism (push-log polling, receipt file) is a binding parameter (see the post-write protocol in `deployment-guide.md` §3).

## 4. storage_adapter Enum + 8-Script Audit

**Enum**: `"local" | "s3"` (s3 covers MinIO / RustFS / any S3-compatible store). The core requires only s3 and local; anything else (gcs/azure-blob) is a binding extension.

**8-script hardcoding check (conclusion: core scripts must not call any object-storage CLI)**:

| Script | Possible hardcoding | Disposition |
|---|---|---|
| `validate-decision-log.sh` | none (pure JSON check) | not needed |
| `detect-conflict.py` | none (pure Python) | not needed |
| `contract-revalidate.sh` | may call `mc cat` to read the compatibility report | changed to read a local file from stdin or `--report-path`; object-store reads are the caller's (CAP-STORE adapter's) job |
| `attention-stall.sh` | none (reads CAP-STATE) | not needed |
| `verification-mismatch-window.sh` | none | not needed |
| `saga-compensate.py` | may call `mc` to write the compensation directive | changed to write a local path; the CAP-STORE adapter uploads |
| `consistency-check.py` | none | not needed |
| `aggregate-vote.sh` | none | not needed |

Scripts handle local files / stdin / stdout only; all object-storage I/O is owned by the CAP-STORE adapter. Any existing `mc` call in a script must be abstracted away.

## 5. RustFS Migration Checklist

```
1. Confirm the RustFS version supports S3 conditional writes
   (If-None-Match/If-Match) and strong read-after-write consistency;
   verify exactly-one-winner with 32 concurrent If-None-Match: * PUTs.
2. Confirm the filesync layer's (container↔RustFS) uploaded-receipt
   mechanism matches the MinIO era; if not, update CAP-STORE T2's
   binding parameters.
3. Verify object fingerprints match after mc mirror / rclone
   migration (client-side SHA-256 comparison); check bucket policy,
   IAM, and lifecycle rules item by item.
4. Check the 8 core scripts for `mc` calls; replace any found with
   local file I/O + the CAP-STORE adapter.
5. Run a Full-tier cross-team task through the golden tests and
   confirm decision_log / contract / handoff behave identically on
   RustFS as on MinIO. (must not be deleted)
```

**Field-test note**: RustFS's S3 compatibility matrix covers object put/get/delete/copy/head and checksums, but the matrix does not explicitly list If-None-Match for conditional writes — **it must be field-tested** (checklist item 1); the compatibility matrix is not a substitute.
