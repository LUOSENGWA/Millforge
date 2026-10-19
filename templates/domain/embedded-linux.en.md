# Domain Fragment: Embedded Linux (embedded-linux)

> T2 domain fragment · source: reference | applies to: worker | spawn domain: embedded-linux

## Context Input (spawn reads from files)

- target board description (SoC/memory/storage/boot chain; structured spec fields)
- existing build system (Buildroot/Yocto/cross-compilation chain configuration; ref = contract)
- current image / root-filesystem fingerprint of the target system (baseline)

## Execution Constraints

- cross-compilation chain versions locked (gcc/glibc/binutils versions into the spec; drift = rework)
- root-filesystem changes: the space budget explicit (embedded storage is constrained — `du` evidence after the build)
- boot-chain changes (init/services/device tree) = R1 (board-level destructive risk; human-locked + rollback image retained)
- service/process changes carry the systemd/init configuration + boot verification logs
- in-loop tagging: no dev board = build-level acceptance + explicit "pending board-level verification"

## Acceptance Points (critic perspective)

- image builds (reproduced with a consistent toolchain) + size within budget
- configuration consistency (device tree/service config vs spec, item by item)
- rollback path: the old image fingerprint retained and restorable (R1 surface)
- board-level verification gap explicitly declared (never pretend)
