# Domain Fragment: Testing / QA (test-qa)

> T2 domain fragment · source: reference | applies to: worker, critic | spawn domain: test-qa

## Context Input (spawn reads from files)

- spec of the object under test (acceptance criteria, ref)
- test baseline (existing test inventory + last result snapshot)
- environment description (test environment/dependencies/data preparation, ref)

## Execution Constraints

- test cases = the spec's acceptance criteria mapped one by one (a criterion with no corresponding test = an acceptance gap, explicitly tagged)
- result evidence: command + full output (file reference) + pass/fail statistics
- failure classification: product defect / test defect / environment issue — the three classes reported separately, never mixed
- data isolation: test data never pollutes production (R1 surface check)
- regression scope declared: the module list this verification covers / does not cover (honest boundary)

## Acceptance Points (critic perspective)

- case-mapping completeness (criterion ↔ test checkable both ways)
- result re-sampling: rerun a sample (≥20% or 5 cases, whichever is more) to verify the evidence is real
- failure reproduction (every "product defect" must be reproducible; not reproducible = downgraded to "suspected")
- environment declaration consistency (the environment where tests ran = the declared environment)
