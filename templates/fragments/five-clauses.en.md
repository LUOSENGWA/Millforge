## Five Clauses (verifier ≠ declarer)

1. **Declaration–verification binding**: before any "done/pushed/created/dispatched" claim, the corresponding tool call must already have succeeded within the same turn. Text output and tool calls are two channels — **saying ≠ doing**
2. **Verifier ≠ declarer**: no producer may accept its own output (the critic runs in an independent fresh context)
3. **Single accountable point**: every project/loop/decision has exactly one accountable stakeholder; the delegation chain is queryable; no collective lock-holding
4. **"Did it" ≠ it was really done**: claimed actions must be cross-verified against system facts (file existence / message records / tool return values)
5. **Signal persistence**: critical state (completion/decision/acceptance) must be persisted as CAP-STATE/CAP-STORE records + signal markers; messages may be lost, state must not
