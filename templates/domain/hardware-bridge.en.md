# Domain Fragment: Hardware Bridge (hardware-bridge)

> T2 domain fragment · source: production (hw-bridge field work)
> Applies to: worker | spawn domain: hw-bridge

## Context Input (spawn reads from files)

- both ends of the bridge (firmware-side protocol + host-side API; dual contract refs)
- protocol definition (frame format/timing/error codes; file ref)
- existing implementation path (ref)

## Execution Constraints

- **dual-end contract synchronization**: firmware-side and host-side changes must be paired (a single-end change = protocol drift = rework required); a protocol frame change = contract semver
- timing-sensitive logic: the latency budget declared (timeout/retransmission parameters into the spec)
- error-path completeness: disconnect/timeout/checksum-failure/out-of-order — all four error handlers mandatory (scorecard injects and verifies each)
- packet-capture/log evidence: protocol verification carries a raw frame dump (file reference)
- real-hardware in-loop = R1 surface (flashing/restarting the device; human informed)

## Acceptance Points (critic perspective)

- protocol consistency: the frame dump checked field by field against the protocol definition
- error injection covers all four classes (each with evidence)
- dual-end version matrix reconciled (firmware version × host driver version compatibility table)
- performance surface: throughput/latency within the declared budget (baseline comparison if available)
