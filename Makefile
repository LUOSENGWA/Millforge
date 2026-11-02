# Millforge developer shortcuts
# Requires: python3 + bash; deps via `pip install -r requirements.txt`

FILE ?= golden-tests/fixtures/bizmarket-team.json

VERSION := $(shell cat VERSION)
PACK_DIR := dist
PACK_NAME := millforge-pack-$(VERSION).tar.gz
PACK_INPUTS := compiler core templates bindings VERSION CHANGELOG.md CHANGELOG.en.md LICENSE README.md README.en.md

.PHONY: test compile validate deps compliance evidence contract schemas bilingual pack

deps:
	pip install -r requirements.txt

test: schemas bilingual
	bash golden-tests/scripts/run-compile-tests.sh
	bash golden-tests/scripts/run-scripts-tests.sh
	bash golden-tests/scripts/run-contract-tests.sh
	python3 core/scripts/check-evidence-refs.py
	python3 core/scripts/check-binding-compliance.py
	python3 golden-tests/tests/test_tier_gate.py
	python3 golden-tests/tests/test_deploy_audit.py

validate:
	python3 compiler/millforge-compile.py validate $(FILE)

compile:
	python3 compiler/millforge-compile.py compile $(FILE) --out out

schemas:
	python3 core/scripts/validate-schemas.py

bilingual:
	python3 core/scripts/check-bilingual.py

compliance:
	python3 core/scripts/check-binding-compliance.py

evidence:
	python3 core/scripts/check-evidence-refs.py

contract:
	bash golden-tests/scripts/run-contract-tests.sh

# Protocol pack for the pinned `requires.millforge` dependency (see TH plugin manifest).
# Deterministic: sorted members, fixed mtime/owner, `gzip -n`; the manifest stays outside
# the tarball so its timestamp cannot break reproducibility.
pack: schemas bilingual
	@set -e; mkdir -p $(PACK_DIR); \
	tar --sort=name --mtime='@0' --owner=0 --group=0 --numeric-owner \
	    --exclude='__pycache__' --exclude='*.pyc' \
	    -cf - $(PACK_INPUTS) | gzip -9n > $(PACK_DIR)/$(PACK_NAME)
	@python3 tools/make-pack-manifest.py --pack $(PACK_DIR)/$(PACK_NAME) --version $(VERSION) --commit "$$(git rev-parse --short=12 HEAD 2>/dev/null || true)"
