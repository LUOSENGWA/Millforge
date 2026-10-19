# Domain Fragment: Market Research (market-research)

> T2 domain fragment · source: llm (pending full-team field test → EXPERIMENTAL)
> Applies to: worker | spawn domain: market-research

## Context Input (spawn reads from files)

- research question list (spec: target market/competitors/time frame)
- existing materials (ref) + data source licensing notes (which sources are usable)

## Execution Constraints

- **numbers must be sourced**: every data point carries a source (report name + date + accessible path/link); unsourced = not acceptable
- separate fact from judgment: facts (sourced) / inferences (derivation chain tagged) / guesses (confidence tagged) — the three classes presented separately
- source quality tiers: primary data (own/official) > industry reports > media coverage > forums (tag the tier when citing)
- freshness tagging: data timestamp + "as of YYYY-MM" (stale data = explicitly downgraded in use)
- compliance: scraping obeys the source's terms; paywalled content is not circumvented (a cited summary + link suffices)
- sensitive information: unpublished competitor intelligence never enters outbound artifacts

## Acceptance Points (critic perspective)

- source checkability rate ≥90% (sample-visit to verify links/paths are valid)
- fact/inference/guess tagging not conflated
- key conclusions' derivation chains complete (conclusion → basis → source, three levels traceable)
- freshness: no stale data presented as current
