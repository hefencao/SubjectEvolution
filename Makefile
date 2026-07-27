.PHONY: test verify-dist release-check release-env release-env-info

PYTHON ?= python
PREVIOUS_WHEEL ?=
RELEASE_ENV ?= .release-env

test:
	PYTHONPATH=src $(PYTHON) -m pytest -q

verify-dist:
	$(PYTHON) scripts/verify_dist.py --project . $(if $(PREVIOUS_WHEEL),--previous-wheel $(PREVIOUS_WHEEL),)

release-check: test verify-dist
	@echo "release-check uses a disposable venv and does not modify the current shell PATH."
	@echo "Use 'make release-env' for a persistent verified environment."

# Build and validate into a persistent venv. Unlike release-check, this leaves
# runnable console scripts under $(RELEASE_ENV)/venv/bin (or Scripts on Windows).
release-env: test
	$(PYTHON) scripts/verify_dist.py --project . --work-dir $(RELEASE_ENV) $(if $(PREVIOUS_WHEEL),--previous-wheel $(PREVIOUS_WHEEL),)
	@echo "Persistent verified environment: $(RELEASE_ENV)/venv"
	@echo "Activate on POSIX/WSL: source $(RELEASE_ENV)/venv/bin/activate"

release-env-info:
	@echo "POSIX/WSL commands live in $(RELEASE_ENV)/venv/bin"
	@echo "Windows commands live in $(RELEASE_ENV)/venv/Scripts"
