## Task Lifecycle (condensed load · full text = protocol §06-LIFECYCLE)

**Recursive decomposition** (every layer is a mini-orchestrator; the loop is isomorphic): task received → judge origin (human = NMH / Agent = triad validation) → confirm understanding → decompose → dispatch to next layer → accept & integrate → report upward.

**Dispatch triad** (missing any one = dispatch invalid; the receiver may reject): task goal / acceptance criteria / delivery location.

**TASK_COMPLETED (mandatory format)**:
```
@{leader} TASK_COMPLETED: {task-id}
Output: {artifact path}
Key conclusions (3–5, one sentence each):
1. ...
```
**Key conclusions are mandatory** — acceptance raw material + handoff raw material + amnesia defense. Summarizing in three sentences right after completion is effortless; it cannot be reconstructed afterwards.

**Dual-channel reporting**: full report in the project room (archive floor: conclusions / output paths / leftovers / next steps) + one-line notice on the originating channel (delivery floor: done + key conclusions + room pointer). Single team = the originating channel is the floor.

**Reply discipline (room noise control)**: only @mention when the other party must act (handoff/blocker/direct question/dependency); pure acknowledgments (thanks/received) → no reply (anti ping-pong); after a completion report is sent, stop and wait for the next task.

**Failure SOP (the orchestrator never does the work)**:
```
Worker anomaly (Internal error / context exceeded / no response >2min)
 Step 0: stop hands — never open the artifact and do it yourself
 Step 1: restart that worker
 Step 2: wait → re-dispatch the same task
 Step 3: still failing after 3 attempts → escalate to human (attach the three attempt records)
Bad quality ≠ failure → go through the NMA review chain, no restart
```

**Worker context isolation**: the native session only schedules + reviews; all implementation goes to fresh spawns (read context from files → write outputs to files → destroyed). Context overflow = isolation violated or spawn context too large; check the file reference chain first.

**State-machine side effects (L1/L2, not self-discipline)**: TASK_COMPLETED baseline emitted = the mechanical side effect of a successful commit; timeout decisions = CAP-STATE fields + CAP-TIMER; conflict/voting/consistency = deterministic scripts. System correctness depends on L1/L2 only.
