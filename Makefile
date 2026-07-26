.PHONY: test verify-dist release-check

PYTHON ?= python
PREVIOUS_WHEEL ?=

test:
	PYTHONPATH=src $(PYTHON) -m pytest -q

verify-dist:
	$(PYTHON) scripts/verify_dist.py --project . $(if $(PREVIOUS_WHEEL),--previous-wheel $(PREVIOUS_WHEEL),)

release-check: test verify-dist
