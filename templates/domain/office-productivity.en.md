# Domain Fragment: Office / Productivity (office-productivity)

> T2 domain fragment · source: reference | applies to: worker | spawn domain: office

## Context Input (spawn reads from files)

- target document/spreadsheet/presentation (ref) + template/style specification (if any = contract)
- data sources (ref; same isolation discipline as the data domain)

## Execution Constraints

- **format fidelity**: edit documents in their native format (docx/xlsx/pptx with the corresponding skill; never downgrade to plain text); table structure/formulas/styling preserved
- large files in chunks: long documents/multi-sheet work processed in chunks, each chunk independently accepted (never the full set into conversation)
- data fidelity: numeric/date/formula conversions lose no precision; verify before/after (row counts/key-value spot-checks)
- version trail: back up the original file (ref) before editing; the final = the acceptance object
- batch operations (multi-file) = single-file verification first, then batch (one OK ≠ all OK)

## Acceptance Points (critic perspective)

- format integrity: opens without corruption / no style loss / formulas valid
- data consistency: key values vs source data, sample-checked (≥5 places)
- structural integrity: table of contents / headers / reference closure
- reproduction: batch operations rerunnable (same input, same output)
