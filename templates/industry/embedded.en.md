# Industry Template: Embedded

> T1 industry fragment · source: production (embedded multi-platform team field work)
> Applies to: worker / leader

## Worker industry constraints

- **Build-chain verification**: the cross-compilation toolchain version + target architecture must be declared (scorecard carries `--version` evidence); SDK version locked (contract)
- **Hardware-in-the-loop**: verification involving real hardware = R1 class (external side effect) — flashing/restarting the target device requires human awareness; if the loop is unavailable = explicitly mark "functional verification to run once the full environment is in place"; never pretend it passed
- **Firmware artifacts**: signature/checksum in the scorecard (fingerprint verifiability)
- **Registers/pins**: changes must cite the datasheet page or register definition (traceable)
- **Context isolation reinforced**: build logs (thousands of lines) always written to files and referenced; spawn reads the build config, never the full source into conversation
- **Version matrix**: MCU model / RTOS version / peripheral driver versions = structured spec fields (drift = rework)

## Leader industry constraints

- decompose by hardware boundary (module/board/driver layer), never by file
- hardware task dependency chains made explicit (hardware-in-the-loop nodes = blocking points; pre-tag the R6 risk)
- firmware release = R1 (human-locked)

## Critic industry constraints (review perspective)

- verification = build + static checks + a reproducible flash/test sequence
- isolation boundary: without the target hardware, mark "pending full environment" (never pretend); 🔵 items limited to CI build status / object-storage artifact fingerprints
