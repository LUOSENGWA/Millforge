# Domain Fragment: Sales / Outreach (sales-outreach)

> T2 domain fragment · source: llm (pending full-team field test → EXPERIMENTAL)
> Applies to: worker | spawn domain: outreach

## Context Input (spawn reads from files)

- target customer profile + contact list (ref)
- product information + pitch conventions (contract) + channel send permissions (which channels are usable)

## Execution Constraints

- **outbound = R1 human-locked**: any outbound email/message/post = sent only after human confirmation. The agent produces drafts + a send plan only; never auto-sends
- draft/final separation: the draft = an artifact (the human-review object); it enters the send queue only after human confirmation
- personalization traceable: each outreach's personalization points carry a source (customer public-information ref); never fabricate "we noticed that you…"
- frequency compliance: contact frequency obeys channel limits (anti-harassment/anti-ban — parameters into the spec)
- customer data = contract surface: contact information enters authorized artifacts only; the list is desensitization-checked before outbound

## Acceptance Points (critic perspective)

- outbound compliance surface: recipient accuracy / no over-promising in content / channel permissions
- personalization authenticity: claimed customer traits traceable
- pitch consistency: no promises beyond the contract (pricing/features/delivery time)
- send records: every outbound has a record (time/recipient/content ref) — auditable
