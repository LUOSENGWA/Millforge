# Domain Fragment: Docs / Content (docs-content)

> T2 domain fragment · source: production (tech-writer field work)
> Applies to: worker | spawn domain: docs

## Context Input (spawn reads from files)

- target document path + existing version (ref)
- fact source inventory (code paths/design docs/API specs, per-item refs)
- glossary (NMH alignment output)

## Execution Constraints

- **fact sourcing**: every technical statement carries a source (path:line / document section / version number); an unsourced claim = not acceptable
- version sensitivity: cited APIs/configs carry version numbers; uncertain = tagged "as of vX, needs verification"
- long documents per section: each section an independent spawn (context = previous section's summary + this section's sources); never the full text
- term consistency: one concept, one term document-wide (the glossary = contract)
- draft/final separated; the final = the acceptance object

## Acceptance Points (critic perspective)

- source checkability rate ≥90% (sample checks: paths exist / line numbers accurate / versions valid)
- structural integrity: table of contents / numbering / cross-reference closure (dead link = rejection item)
- code-consistency spot-check (key configs/commands actually verified executable)
