# Domain Fragment: MCU / Firmware (mcu)

> T2 domain fragment · source: production (mcu-dev field work)
> Applies to: worker | spawn domain: mcu-driver

## Context Input (spawn reads from files)

- target MCU model + peripheral inventory (structured spec fields)
- register/peripheral definitions (datasheet page or header-file ref)
- existing driver code paths (ref) + build configuration (toolchain version = contract)

## Execution Constraints

- toolchain locked: compiler version + target architecture declared (scorecard carries `--version` evidence)
- a register change must carry its basis (datasheet page / register definition ref); never write offsets from memory
- interrupt/timing-sensitive logic: the interrupt-context constraints are tagged (non-blockable / priority)
- in-loop verification tagged: no target hardware = "functional verification to run once the full environment is in place"; never pretend
- flashing/restarting the target device = R1 (human informed)
- compile warnings: new warnings must be handled or explicitly waived (the waiver recorded in decision_log)

## Acceptance Points (critic perspective)

- reproducible build (matching toolchain version → matching artifact; fingerprint comparison)
- static checks (MISRA-class, if configured) + impact-surface review
- register offset / clock configuration spot-check (against the definition files)
- without target hardware, the verification gap is explicitly tagged (never pretend it passed)
