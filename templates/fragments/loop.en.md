## Loop Primitive (condensed load · full text = protocol §10-LOOP)

**Positioning**: goal locked → iterate (dispatch → independent verification) → achieved? stop : re-plan; runs within budget. A loop contains tasks without being a task — tasks inside an iteration still go through R1-R6/NMH/critic.

**loop_spec (human-locked; execution units may not self-start or expand budget)**: goal_ref (human-locked spec) / stop_condition (**externally decidable binary condition**, never "the model declares done") / iteration_budget {max_iterations, max_human_touch (aggregated from goal_ref)} / convergence_rule {no_progress_window, progress_signal (**magnitude-aware**: acceptance_delta/score_delta — not "there was a change")} / re_plan_rule {max_replans} / termination_action[].

**Five phases (CAP-STATE driven; the driver derives idempotently)**:
```
DISPATCH (fresh spawn, X4 deadline) → EXECUTE (structured return; self_reported_status is data, not a conclusion)
→ VERIFY (critic independent acceptance, not parent self-verification) → JUDGE (achieved → stop / budget + progress → re-plan /
no progress → stalled + escalate / budget exhausted → exhausted + escalate / undecidable → R6 escalate) → RECORD (append to history; never into the driver's context)
```

**Driver discipline** (you are the accountable orchestrator of the loop scope):
1. authoritative state lives only in CAP-STATE — on every wake you **idempotently re-derive** next_action; no incremental notes, no session-memory dependence
2. you **may not self-declare the stop_condition achieved** (achieved = readable only after the predicate/critic wrote it)
3. the native context keeps only iteration summaries {index, verdict, progress_signal, key_refs[]}; full outputs go to a review spawn
4. your crash does not affect authoritative state (the scheduler keeps triggering + escalating)

**Anti-bypass (hard rules)**:
- anti-fragmentation: ≥2 tasks with the same goal_ref and an artifact dependency → must share one loop container; the simple tier requires fragmentation_justification
- anti-padding: a single change smaller than min_substantive_change → low_yield demotion; consecutive low_yield counts into no_progress_window
- cross-team reflow (single_user only): ≤{{max_reflow}} reflows sharing the budget pool; **2 consecutive reflows with the same criterion and same fingerprint = semantic stall, terminate immediately** (even if budget remains)

**Tiers**: simple not enabled (local retry ≤3 → escalate) ｜ standard conditionally enabled (converges only after multiple rounds) ｜ full by default (goal needs iteration) + cross-team feedback loops mandatory.
