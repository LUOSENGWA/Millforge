# Migration Human-Confirmation Checklist (B-7)

> After the scaffold generator produces `team.json`, **tick every item** before entering phase 2 (parallel dual-write). Any unticked item = stop.

## A. Roles and roster

- [ ] `roles[]` covers **every** role of the existing team (cross-check the phase-1 difference report; no unknown roles)
- [ ] Each `kind` is correct (coordinator / leader / worker / critic) — the generator infers from filenames, so **human review is mandatory**
- [ ] Human entries in `roster[]` are replaced with real identities (`TODO-human-a` removed); `weight` confirmed by the person
- [ ] `mode` matches the real team shape (single_user = one human; multi_user = several)

## B. Charter and boundaries

- [ ] `charter.mission` is **transcribed** from the existing charter (not rewritten, not guessed)
- [ ] `scope` / `non_goals` unchanged from before migration; any change must be recorded in the cutover record

## C. Protocol parameters

- [ ] `protocol.fuse_threshold` / `fuse_window_seconds` match operational requirements (default 2 / 30s)
- [ ] Per-role `budget` (line budget) confirmed against the new protocol baseline (coordinator<=500 / leader<=250 / worker<=150 / critic<=150)
- [ ] `decision_class` labels (R1–R6) confirmed by the team's humans — **a wrong class costs B-10 saga compensation**

## D. Compile and compare (phase-1 exit)

- [ ] `millforge validate team.json` passes
- [ ] `millforge compile team.json --out shadow/` succeeds, artifacts within budget
- [ ] The difference report vs the legacy SOULs has been reviewed (added fragments = protocol increments, not behaviour drift)

## E. Phase-2 gate (parallel dual-write)

- [ ] >= 10 decision_log dual-write samples, human-verified consistent
- [ ] contract_snapshot fingerprint matches the contract version (`contract-revalidate.sh` exit 0)
- [ ] Critic isolation is live (reviews run in the native session, never via spawn)

## F. Phase-3 gate (cutover)

- [ ] Rollback plan written (how the old flow is restored, how long it takes)
- [ ] Cutover window agreed with ops (off-peak)
- [ ] First post-cutover decision_log has no schema violations (`validate-decision-log.sh` exit 0)

---
**Any failed item = BLOCKED** — record the reason before continuing. This checklist is archived with the team and never enters `golden-tests/`.
