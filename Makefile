.PHONY: format lint type policy check

CI_SHARED_ROOT ?= $(HOME)/projects/ci_shared
export CI_SHARED_ROOT
export PYTHONPATH := $(CI_SHARED_ROOT)$(if $(PYTHONPATH),:$(PYTHONPATH))
export PYTHONDONTWRITEBYTECODE := 1

# Repository-specific overrides (set before including ci_shared.mk)
# Add pytest warning filters to allow ResourceWarning/PytestUnraisableExceptionWarning (from async test cleanup)
SHARED_PYTEST_EXTRA = -W "ignore::ResourceWarning" -W "ignore::pytest.PytestUnraisableExceptionWarning"

# Keep pylint focused on actionable failures and ensure it can resolve src-layout imports.
PYLINT_ARGS = --errors-only --init-hook="import sys; sys.path.insert(0, 'src'); sys.path.insert(0, 'tests')" --extension-pkg-allow-list=orjson,redis

# Include shared CI checks
include ci_shared.mk

# Convenience commands for local development consistency.
format:
	isort --profile black $(FORMAT_TARGETS)
	black $(FORMAT_TARGETS)

lint:
	$(PYTHON) -m compileall $(FORMAT_TARGETS)
	pylint -j 1 $(PYLINT_ARGS) $(SHARED_PYLINT_TARGETS)

type:
	pyright --warnings $(SHARED_PYRIGHT_TARGETS)

policy:
	$(PYTHON) -m ci_tools.scripts.policy_guard

check: shared-checks ## Run format checks, static analysis, and tests.
