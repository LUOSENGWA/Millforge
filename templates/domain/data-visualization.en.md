# Domain Fragment: Data Visualization (data-visualization)

> T2 domain fragment · source: reference | applies to: worker | spawn domain: viz

## Context Input (spawn reads from files)

- data + field semantics (ref; same isolation discipline as data-analysis)
- visualization goal (audience/purpose/channel — decides precision and format)
- design specification (palette/fonts/template; if any = contract)

## Execution Constraints

- chart type matches the data semantics (time series → line / categories → bar / proportions → pie with caution)
- honest axes/units/scales: no truncation that misleads (a broken axis must be tagged); units shown in the chart
- reproduction: charts are script-generated (data ref + script ref), never hand-assembled
- large/small screen dual versions (when the channel requires it); an interactive prototype = the interactive points documented (non-interactive channels downgrade to static + annotations)
- data desensitization: outbound charts check sensitive fields (customer names/precise amounts, per the spec's desensitization rules)

## Acceptance Points (critic perspective)

- numeric consistency: key values on the chart vs the data source, sample-checked
- mislead check: axis origin / broken axis / proportions / color semantics
- reproduction: rerunning the script yields matching output
- readability: title/legend/annotations complete (a cold reader grasps the theme in 3 seconds)
