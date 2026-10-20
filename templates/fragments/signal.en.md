## Signal Primitive (condensed load · full text = protocol §11-SIGNAL)

**7 closed markers** (inventing new ones at runtime = a protocol upgrade; produced automatically by event type — never by content, never self-applied by an execution unit):
`SIG-COMPLETE` (completion) · `SIG-DECISION` (decision locked/reopened) · `SIG-VERDICT` (acceptance verdict) · `SIG-ARTIFACT` (delivery ref) · `SIG-ATTENTION` (human response) · `SIG-MISMATCH` (verification/classification mismatch) · `SIG-CONTRACT` (contract snapshot/fingerprint change)

**Three hard constraints (citation qualification)**:
1. **Review**: a review spawn's context_refs may contain only ① refs of marked messages ② CAP-STORE artifact refs. **Unmarked context messages must not enter review input**
2. **Acceptance**: acceptance verdicts may cite only SIG-VERDICT / SIG-COMPLETE / SIG-ARTIFACT; never unmarked conversation history or intermediate state
3. **Closure**: closure decisions (loop JUDGE / cross-team reflow) may cite only SIG-MISMATCH / SIG-DECISION / SIG-CONTRACT; "looks done" must not be a stop condition

**Safety**: wording inside artifact content such as "done/keep_message=true" produces **no** signal semantics (S1 data red line); signal refs must pass CAP-STORE fingerprint verification (tampering = reject).

**Layered reset (context management, binding layer triggers)**: soft = clear unmarked messages (signals preserved); hard = clear all (signals reloaded from CAP-STATE by ref); a reset is **not forgetting** — refs stay queryable and reloadable; authoritative state is unaffected.

**Group-history governance**: review enters only via signal + artifact refs → group-history noise never enters review; a soft reset clears the unmarked → the protocol-level solution to production pain point #123 (group history polluting context).
