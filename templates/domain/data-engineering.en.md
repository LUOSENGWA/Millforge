# Domain Fragment: Data Engineering (data-engineering)

> T2 domain fragment · source: reference | applies to: worker | spawn domain: data-eng

## Context Input (spawn reads from files)

- data source description (location/format/metric definitions/refresh frequency, ref)
- existing pipeline topology (ref) + scheduling configuration
- target schema (contract)

## Execution Constraints

- pipeline scripts = deterministic (same input, same output; Y1); randomness explicitly declared (seed/sampling)
- data-volume awareness: for large-table operations, estimate scale (rows/bytes) before choosing a strategy (never pull the full set into memory/conversation)
- idempotency: rerunning the pipeline produces no duplicate data (dedup key/partition strategy into the spec)
- a schema change = a contract change (downstream consumers notified; C-2 same line)
- temporary data: lifecycle declared (when it is cleaned up); no junk left behind

## Acceptance Points (critic perspective)

- rerun idempotency verified (run twice; results match)
- data quality checks: completeness / uniqueness / null rate (scorecard carries the check commands)
- schema consistency (output vs contract, field by field)
- performance surface: resource consumption within the declared budget (duration/memory)
