# Industry Template: Content

> T1 industry fragment · source: reference (tech-writer field work + design derivation)
> Applies to: worker / leader

## Worker industry constraints

- **Fact sourcing**: every technical statement carries a source (doc/code path/version); an unsourced technical claim = not acceptable
- **Version sensitivity**: cited APIs/configs carry version numbers; an outdated version = explicitly tagged "as of vX"
- **Term consistency**: the glossary comes first (NMH term-alignment log → carried through the final document); one term per concept document-wide
- **Context isolation reinforced**: long documents are spawned per section (each section an independent spec + context reference to the previous section's summary; never the full text)
- **Draft-final separation**: intermediate drafts kept as artifacts (audit chain); the final = the acceptance object
- **Format contract**: template/style guide = contract artifact (pinning; a revision = semver minor + re-verification)

## Leader industry constraints

- decomposition = document structure (sections), never one-line tasks
- fact-dense sections (API specs/configs) = review category (NMA Checklist: every source individually checkable)
- publication = R1 (externally visible); internal docs = R4

## Critic industry constraints (review perspective)

- source checkability rate ≥90% (sample-verify that sources are real); unsourced technical claims = rejection items
- structural integrity (table of contents / numbering / reference closure / term consistency)
- version-tag spot-check (whether cited API/config versions are currently valid)
