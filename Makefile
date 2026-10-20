# Millforge developer shortcuts
# Requires: python3 + bash; deps via `pip install -r requirements.txt`

FILE ?= golden-tests/fixtures/bizmarket-team.json

.PHONY: test compile validate deps

deps:
	pip install -r requirements.txt

test:
	bash golden-tests/scripts/run-compile-tests.sh
	bash golden-tests/scripts/run-scripts-tests.sh

validate:
	python3 compiler/millforge-compile.py validate $(FILE)

compile:
	python3 compiler/millforge-compile.py compile $(FILE) --out out
