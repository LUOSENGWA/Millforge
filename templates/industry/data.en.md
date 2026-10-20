# Industry Template: Data

> T1 industry fragment · source: reference (data-analyst/report-writer field work + design derivation)
> Applies to: worker / leader

## Worker industry constraints

- **Data sourcing**: every conclusion carries a data source (table/file/query + timestamp); a metric-definition change = a new artifact (never overwrite)
- **Reproducible**: analysis scripts/queries persisted (CAP-STORE ref); a "mental math" conclusion = not acceptable
- **Numeric precision**: amounts/ratios/statistics explicitly declare precision and rounding rules; units go into the spec
- **Dataset versioning**: the input data snapshot (fingerprint) goes into the task spec — upstream data changed = cross-version re-verification (C-2 same-line logic)
- **Context isolation reinforced**: large tables/raw data never enter conversation — spawn reads files, conclusions write to files; conversation carries only summaries + refs
- **Charts**: generation scripts are rerunnable (same data, same output; Y1 determinism)

## Leader industry constraints

- decomposition = data pipeline stages (ingest → clean → analyze → present), each stage an independent artifact
- data quality checks (completeness/anomalies) = a front-loaded scorecard item, not after-the-fact remediation
- cross-dataset tasks fix the metric-definition contract (contract) first

## Critic industry constraints (review perspective)

- verification = rerun the script/query and compare values (sampling OK; full volume by scale); metric-definition reconciliation
- numeric scorecard lines must carry a reproduction command (not "looks right")
