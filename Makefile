# Millforge developer shortcuts
# Requires: python3 + bash; deps via `pip install -r requirements.txt`

FILE ?= golden-tests/fixtures/bizmarket-team.json

.PHONY: test compile validate deps compliance evidence

deps:
	pip install -r requirements.txt

test:
	bash golden-tests/scripts/run-compile-tests.sh
	bash golden-tests/scripts/run-scripts-tests.sh
	python3 core/scripts/check-evidence-refs.py
	python3 core/scripts/check-binding-compliance.py
	python3 golden-tests/tests/test_tier_gate.py

validate:
	python3 compiler/millforge-compile.py validate $(FILE)

compile:
	python3 compiler/millforge-compile.py compile $(FILE) --out out

compliance:
	python3 core/scripts/check-binding-compliance.py

evidence:
	python3 core/scripts/check-evidence-refs.py
