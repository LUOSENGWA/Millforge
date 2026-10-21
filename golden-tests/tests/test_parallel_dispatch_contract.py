#!/usr/bin/env python3
"""M4 parallel-dispatch scene contract test against the seed fixture.

Fixtures: golden-tests/fixtures/parallel-9/ (10 task state.json + inbox.jsonl,
normalized from a nine-task pilot). Each invariant PD-1..PD-7 declared in
bindings/agentteams/parallel-dispatch.md is asserted on the seed data.
Deterministic; no network; no runtime required.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = ROOT / "golden-tests" / "fixtures" / "parallel-9"
TERMINAL = {"done", "failed-budget", "killed", "blocked-by-gate"}
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

failures: list[str] = []
N_CHECKS = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global N_CHECKS
    N_CHECKS += 1
    if not cond:
        failures.append(f"{name}: {detail}")


# ---- load fixtures ---------------------------------------------------------
tasks: dict[str, dict] = {}
for d in sorted(p for p in FIX.iterdir() if p.is_dir()):
    f = d / "state.json"
    if not f.exists():
        failures.append(f"inv1: missing state.json in {d.name}")
        continue
    tasks[d.name] = json.loads(f.read_text(encoding="utf-8"))

inbox = [
    json.loads(line)
    for line in (FIX / "inbox.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]

check("inv1_fixtures_loaded", len(tasks) == 10, f"expected 10 tasks, got {len(tasks)}")
check("inv1_inbox_loaded", len(inbox) == 7, f"expected 7 inbox events, got {len(inbox)}")

# ---- PD-1 single source of truth on disk ----------------------------------
for name, st in tasks.items():
    check(f"inv1_task_field_{name}", st.get("task") == name,
          f"task field {st.get('task')!r} != dirname {name}")
    check(f"inv1_status_{name}", st.get("status") in TERMINAL | {"running"},
          f"unexpected status {st.get('status')!r}")
for ev in inbox:
    check(f"inv1_inbox_ref_{ev.get('task')}", ev.get("task") in tasks,
          f"inbox references unknown task {ev.get('task')!r}")

# ---- PD-2 dispatch-time conflict gate (zero execution cost) ----------------
gates = [ev for ev in inbox if ev.get("status") == "blocked-by-gate"]
check("inv2_gate_events", len(gates) >= 2,
      f"expected >=2 blocked-by-gate events, got {len(gates)}")
check("inv2_gate_reason",
      all("files_to_touch" in (ev.get("detail") or "") for ev in gates),
      "gate events must cite files_to_touch overlap")
for ev in gates:
    st = tasks.get(ev["task"], {})
    check(f"inv2_zero_cost_{ev['task']}",
          not st.get("session_id") and not st.get("pid") and not st.get("started_at"),
          f"{ev['task']} has execution fields despite dispatch rejection")

# ---- PD-3 terminal state before cleanup (state and inbox agree) ------------
state_term = {n for n, s in tasks.items() if s.get("status") in TERMINAL}
inbox_term = {(e["task"], e["status"]) for e in inbox if e.get("status") in TERMINAL}
for n in sorted(state_term):
    check(f"inv3_inbox_has_{n}", (n, tasks[n]["status"]) in inbox_term,
          f"terminal state without matching inbox event: {n}")
for t, s in sorted(inbox_term):
    check(f"inv3_state_has_{t}", tasks.get(t, {}).get("status") == s,
          f"inbox terminal without matching state: {t}")

# ---- PD-4 receipt is a first-class artifact --------------------------------
# blocked-by-gate never executed: no exit_code/wall_s expected (see PD-2)
executed_term = {n for n in state_term if tasks[n]["status"] != "blocked-by-gate"}
for n in sorted(executed_term):
    st = tasks[n]
    check(f"inv4_exit_code_{n}", str(st.get("exit_code", "")).lstrip("-").isdigit(),
          f"missing numeric exit_code on {n}")
    check(f"inv4_wall_s_{n}", str(st.get("wall_s", "")).isdigit(),
          f"missing numeric wall_s on {n}")
    check(f"inv4_finished_at_{n}", bool(st.get("finished_at")),
          f"missing finished_at on {n}")
check("inv4_bounded_budget_failure",
      any(st.get("status") == "failed-budget" and st.get("exit_code") == "55"
          for st in tasks.values()),
      "seed must contain the rc=55 bounded budget failure")
check("inv4_killed",
      any(st.get("status") == "killed" and st.get("exit_code") == "137"
          for st in tasks.values()),
      "seed must contain the rc=137 killed state")

# ---- PD-5 notifications are 3-line pointers (no payload) -------------------
check("inv5_pointer_details",
      all(len((e.get("detail") or "")) <= 64 for e in inbox),
      "every inbox event must carry a short pointer, not a payload")
check("inv5_structured_details",
      all(re.fullmatch(r"[\w .=/<>-]+", e.get("detail") or "") for e in inbox),
      "detail must be structured short text (no prose payload)")

# ---- PD-6 watchdog backstop (liveness inputs derivable) --------------------
for n, st in tasks.items():
    if st.get("status") == "running":
        check(f"inv6_pid_{n}", str(st.get("pid", "")).isdigit(),
              f"running task {n} must carry a numeric pid for liveness checks")
        check(f"inv6_updated_at_{n}", bool(st.get("updated_at")),
              f"running task {n} must carry updated_at for stall derivation")
for e in inbox:
    st = tasks.get(e["task"], {})
    check(f"inv6_ts_consistent_{e['task']}",
          e.get("ts") in (st.get("updated_at"), st.get("finished_at")),
          f"inbox ts {e.get('ts')} not derivable from state of {e['task']}")

# ---- PD-7 isolation (fresh per-task session ids) ---------------------------
sids = [st["session_id"] for st in tasks.values() if st.get("session_id")]
check("inv7_sessions_present", len(sids) == 8,
      f"expected 8 spawned tasks with session_id, got {len(sids)}")
check("inv7_unique_sessions", len(set(sids)) == len(sids),
      "session ids must be unique per task (fresh context, X1)")
check("inv7_uuid_shape", all(UUID_RE.fullmatch(s) for s in sids),
      "session ids must be UUID-shaped")

if failures:
    print(json.dumps({"ok": False, "checks": N_CHECKS, "failures": failures},
                     ensure_ascii=False, indent=1))
    sys.exit(1)
print(json.dumps({"ok": True, "checks": N_CHECKS, "tasks": len(tasks),
                  "events": len(inbox)}, ensure_ascii=False))
