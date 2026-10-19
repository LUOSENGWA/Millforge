# Domain Fragment: Desktop App (desktop)

> T2 domain fragment · source: reference | applies to: worker | spawn domain: desktop

## Context Input (spawn reads from files)

- project structure + target module (ref) + target platform matrix (OS/architecture)
- existing build configuration (Makefile/cmake/CMakeLists = contract)

## Execution Constraints

- cross-platform build: every platform in the target matrix must build (scorecard per item)
- platform API differences handled explicitly (conditional compilation / adapter layer); never assume a single platform
- packaged artifact fingerprint (checksum) into the scorecard
- local verification = executable on the target OS; cross-platform = tagged "pending verification on that platform's environment"

## Acceptance Points (critic perspective)

- build matrix reproducible per item; artifacts launch (target platform)
- dependencies locked (version-file fingerprint)
- regression: all existing tests green + impact-surface check
