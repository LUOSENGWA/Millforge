# Domain Fragment: Mobile (mobile)

> T2 domain fragment · source: production | applies to: worker | spawn domain: mobile-app (Android/iOS)

## Context Input (spawn reads from files)

- project structure + target module code paths (refs)
- target platform / SDK version matrix (structured spec fields)
- UI design mock (if any)

## Execution Constraints

- platform versions locked: minSdk/targetSDK/deployment target = spec fields (drift = rework)
- real-device/emulator verification tagged: loop unavailable = "functional verification to run once the full environment is in place"; never pretend it passed
- a permission declaration change = contract surface (permissions = a user-visible contract)
- build verification: assemble passes + target Activity/page launches (scorecard carries log evidence)
- artifact = patch/ref + key logs (file references)

## Acceptance Points (critic perspective)

- build + static checks + operation-path verification for the parts that can run in-loop
- boundaries: permission-denied / low-end device / network-dropout — the three states
- regression: impact-surface reference check (cross-module calls)
