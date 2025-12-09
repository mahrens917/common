.PHONY: format lint type policy check

CI_SHARED_ROOT ?= $(HOME)/ci_shared
export PYTHONPATH := $(CI_SHARED_ROOT)$(if $(PYTHONPATH),:$(PYTHONPATH))
export PYTHONDONTWRITEBYTECODE := 1

# Add pytest warning filters to allow ResourceWarning/PytestUnraisableExceptionWarning (from async test cleanup)
SHARED_PYTEST_EXTRA = -W "ignore::ResourceWarning" -W "ignore::pytest.PytestUnraisableExceptionWarning"

# Include shared CI checks
include ci_shared.mk

# Convenience commands for local development consistency.
format:
	isort --profile black $(FORMAT_TARGETS)
	black $(FORMAT_TARGETS)

lint:
	$(PYTHON) -m compileall src tests
	pylint -j 1 src tests

type:
	pyright src

policy:
	$(PYTHON) -m ci_tools.scripts.policy_guard

check: shared-checks ## Run format checks, static analysis, and tests.
