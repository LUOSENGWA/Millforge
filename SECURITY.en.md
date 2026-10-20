# Security Policy

## Supported versions

Only the latest release (see `VERSION`) receives security fixes. Historical versions are not back-ported.

## Reporting a vulnerability

**Do not open a public issue.** Use GitHub's private channel:

1. Repository page → **Security** → **Report a vulnerability** (GitHub Security Advisories); or
2. If that entry is unavailable, open an issue with no technical detail titled `security contact requested`; maintainers will open a private channel.

Please include: affected version, reproduction steps, impact (remotely triggerable? requires local file-write access?), and a suggested fix direction (optional).

## Response

- Acknowledgement: within 7 days.
- Fix and disclosure: timeline negotiated by severity; after the fix ships, it is recorded in the CHANGELOG and, where appropriate, published in a Security Advisory.

## Scope

This repo is **protocol definitions + a compiler** (no network, no LLM, deterministic output). Main risk surfaces:

| Surface | Notes |
|---|---|
| Compiler input | malicious `team.json` / template files → path traversal, resource exhaustion (line-budget gate); do not use bypass parameters beyond `--budget-override` on untrusted input |
| Templates / fragments | third-party template injection (placeholder rendering); contributed templates must pass the golden gates and the sensitive scrub |
| Generated artifacts | runtime-specific names inside generated SOUL.md violate the generic-term discipline (not a security bug, but CI will reject it) |

Out of scope: vulnerabilities in downstream runtimes (AgentTeams / QwenPaw / any binding runtime) — report those to the respective project; `bindings/` docs here only describe integration.
