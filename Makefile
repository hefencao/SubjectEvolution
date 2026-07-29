.PHONY: test test-src parity parity-gpu conda-sync conda-check verify-dist release-check release-env release-env-info

PYTHON ?= python
PREVIOUS_WHEEL ?=
RELEASE_ENV ?= .release-env

# Normal test path after ``make conda-sync``.
test:
	$(PYTHON) scripts/run_test_shards.py --project . --shards 5 --report docs/v0.66/FINAL_TEST_REPORT.json

# Bootstrap path for CI or a clean checkout that is not installed editable.
test-src:
	PYTHONPATH=src $(PYTHON) scripts/run_test_shards.py --project . --shards 5 --report docs/v0.66/FINAL_TEST_REPORT.json

# CPU-emulated stage parity always runs; real-device tests run when CUDA/CuPy is available.
parity:
	$(PYTHON) -m pytest -q tests/test_parity.py

# Target-GPU release gate. Fails instead of skipping when no usable CUDA/CuPy device exists.
parity-gpu:
	rm -rf docs/v0.66/GPU_PARITY_REPORTS
	mkdir -p docs/v0.66/GPU_PARITY_REPORTS
	SE_REQUIRE_GPU_PARITY=1 SE_GPU_PARITY_REPORT_DIR=docs/v0.66/GPU_PARITY_REPORTS $(PYTHON) -m pytest -q tests/test_parity.py
	$(PYTHON) scripts/summarize_gpu_parity_reports.py --project . --reports-dir docs/v0.66/GPU_PARITY_REPORTS --output docs/v0.66

# Preferred local workflow. Source changes are immediately visible after this
# one editable install; rerun only after changing pyproject entry points,
# dependencies, version metadata, or moving the checkout.
conda-sync:
	$(PYTHON) scripts/check_version_consistency.py --project .
	$(PYTHON) scripts/clean_project_bytecode.py --project .
	@test -n "$$CONDA_PREFIX" || (echo "Activate the intended conda environment first." && exit 2)
	$(PYTHON) -m pip install --no-deps --no-build-isolation -e .
	$(PYTHON) scripts/verify_conda_editable.py --project . --require-conda

conda-check:
	$(PYTHON) scripts/run_conda_check.py --project . --shards 5 --docs-dir docs/v0.66

verify-dist:
	$(PYTHON) scripts/verify_dist.py --project . $(if $(PREVIOUS_WHEEL),--previous-wheel $(PREVIOUS_WHEEL),)

release-check:
	$(PYTHON) scripts/run_release_check.py --project . --test-report docs/v0.66/FINAL_TEST_REPORT.json --report docs/v0.66/RELEASE_CHECK_REPORT.json $(if $(PREVIOUS_WHEEL),--previous-wheel $(PREVIOUS_WHEEL),)
	@echo "release-check is an artifact audit only; conda-sync is the local runtime workflow."

release-env: test-src
	$(PYTHON) scripts/verify_dist.py --project . --work-dir $(RELEASE_ENV) $(if $(PREVIOUS_WHEEL),--previous-wheel $(PREVIOUS_WHEEL),)
	@echo "Persistent artifact-validation environment: $(RELEASE_ENV)/venv"

release-env-info:
	@echo "Local conda runtime: make conda-sync"
	@echo "Artifact validation only: make release-check or make release-env"
