# Domain Fragment: RTOS / Firmware (rtos-firmware)

> T2 domain fragment · source: reference | applies to: worker | spawn domain: rtos

## Context Input (spawn reads from files)

- RTOS type + version (FreeRTOS/Zephyr/RT-Thread…; spec field = contract)
- task inventory (priority/stack size/period; ref)
- target hardware description (same as the mcu domain)

## Execution Constraints

- task resource declarations: each task/queue/semaphore's stack size + priority into the spec (never guess defaults)
- critical sections / shared resources: the mutual-exclusion strategy explicit (lock/queue/lock-free); a new shared resource = declared
- watchdog / low-power changes = R1 (system-level behavior; human-locked)
- stack-overflow checks: the build carries a stack-usage report (evidence in the scorecard)
- priority-inversion risk: a new lock requires checking the holding task's priority chain

## Acceptance Points (critic perspective)

- resource declarations vs actual (stack/queue configuration checked item by item)
- priority-chain review (the holding paths of new locks)
- determinism: no implicit blocking (in-task IO declared)
- build + static analysis (if configured) reproducible
