VENV ?= .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

VAULT_SCRIPTS := vendor/vault-ld-scripts
DEMO_VAULT    := demos/vault-ld
BUILD         := build/vault-ld
REHYDRATED    := build/rehydrated
REBUILD       := build/rehydrated-build

export PYTHONPATH := $(VAULT_SCRIPTS):$(CURDIR)/src

.PHONY: venv install test seed roundtrip clean

venv:
	python3 -m venv $(VENV)

install: venv
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

seed: install
	$(PY) -m core_system.wiki seed --bot seed

test: install
	$(PY) -m unittest discover -s tests -v

# Vault-LD converter roundtrip (markdown remains master; app write-back stays off)
roundtrip: install
	rm -rf $(BUILD) $(REHYDRATED) $(REBUILD)
	mkdir -p $(BUILD)
	$(PY) $(VAULT_SCRIPTS)/vault_to_rdf.py "$(DEMO_VAULT)" --source --out-dir $(BUILD)
	$(PY) $(VAULT_SCRIPTS)/rdf_to_vault.py $(REHYDRATED) $(BUILD)/schema.ttl $(BUILD)/data.ttl --context "$(DEMO_VAULT)/context.jsonld"
	mkdir -p $(REBUILD)
	$(PY) $(VAULT_SCRIPTS)/vault_to_rdf.py $(REHYDRATED) --source --out-dir $(REBUILD)
	$(PY) $(VAULT_SCRIPTS)/compare_builds.py $(BUILD) $(REBUILD)

clean:
	rm -rf $(VENV) build data/agent-memory wiki .pytest_cache src/*.egg-info *.egg-info
