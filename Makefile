.PHONY: test test-src conda-sync conda-check verify-dist release-check release-env release-env-info

PYTHON ?= python
PREVIOUS_WHEEL ?=
RELEASE_ENV ?= .release-env

# Normal test path after ``make conda-sync``.
test:
	$(PYTHON) -m pytest -q

# Bootstrap path for CI or a clean checkout that is not installed editable.
test-src:
	PYTHONPATH=src $(PYTHON) -m pytest -q

# Preferred local workflow. Source changes are immediately visible after this
# one editable install; rerun only after changing pyproject entry points,
# dependencies, version metadata, or moving the checkout.
conda-sync:
	@test -n "$$CONDA_PREFIX" || (echo "Activate the intended conda environment first." && exit 2)
	$(PYTHON) -m pip install --no-deps --no-build-isolation -e .
	$(PYTHON) scripts/verify_conda_editable.py --project . --require-conda

conda-check: conda-sync
	$(PYTHON) -m pytest -q
	$(PYTHON) scripts/verify_conda_editable.py --project . --require-conda --smoke --report docs/v0.40/CONDA_EDITABLE_VALIDATION_REPORT.json

verify-dist:
	$(PYTHON) scripts/verify_dist.py --project . $(if $(PREVIOUS_WHEEL),--previous-wheel $(PREVIOUS_WHEEL),)

release-check: test-src verify-dist
	@echo "release-check is an artifact audit only; conda-sync is the local runtime workflow."

release-env: test-src
	$(PYTHON) scripts/verify_dist.py --project . --work-dir $(RELEASE_ENV) $(if $(PREVIOUS_WHEEL),--previous-wheel $(PREVIOUS_WHEEL),)
	@echo "Persistent artifact-validation environment: $(RELEASE_ENV)/venv"

release-env-info:
	@echo "Local conda runtime: make conda-sync"
	@echo "Artifact validation only: make release-check or make release-env"
