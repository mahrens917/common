# Common: Claude Guide

Shared Python utilities library used across multiple trading system repositories. Code lives in `src/common/`, tests mirror the layout in `tests/`.

## Quick Commands
- Run CI/automation with `make check` or `python -m ci_tools.ci --model gpt-5-codex` (delegates to `ci_tools/scripts/ci.sh` through `ci_shared.mk`).
- Tests: `pytest tests/ --cov=src --cov-fail-under=80 --strict-markers --cov-report=term -W error` (serial execution). Coverage guard enforces 80%.
- Formatting/type/lint: `make format`, `make type`, `make lint`.

## Code Hygiene
- Avoid adding fallbacks, duplicate code, backward-compatibility risks, fail-fast gaps, or dead code; if you see existing issues, call them out and fix them.
- Prefer config JSON files over new environment variables; only add ENV when required and document it.

## Duplicate Code Rule
- Search `src/common/` before adding helpers (`rg "def <name>" src`). Many utilities already exist.
- If a duplicate surfaces, centralize the best version, update callers to import it, and document the delegation.

## CI Pipeline (exact order)
- `codespell` -> `vulture` -> `deptry` -> `gitleaks` -> `bandit_wrapper` -> `safety scan` (skipped with `CI_AUTOMATION`) -> `ruff --fix` -> `pyright --warnings` -> `pylint` -> `pytest` -> `coverage_guard` -> `compileall`.
- Limits: classes <=100 lines; functions <=80; modules <=400; cyclomatic <=10 / cognitive <=15; inheritance depth <=2; <=15 public / 25 total methods; <=5 instantiations in `__init__`/`__post_init__`; `unused_module_guard --strict`; documentation guard expects README/CLAUDE/docs hierarchy.
- Policy guard reminders: banned tokens (`legacy`, `fallback`, `default`, `catch_all`, `failover`, `backup`, `compat`, `backwards`, `deprecated`, `legacy_mode`, `old_api`, `legacy_flag`, TODO/FIXME/HACK/WORKAROUND), no broad/empty exception handlers, no literal fallbacks in `.get`/`setdefault`/ternaries/`os.getenv`/`if x is None`, and no `time.sleep`/`subprocess.*`/`requests.*` inside `src`.
- Prep: `tool_config_guard --sync` runs up front; PYTHONPATH is set to include `~/projects/ci_shared`.

## Do/Don't
- Do fix the code rather than weakening checks (`# noqa`, `# pylint: disable`, `# type: ignore`, `policy_guard: allow-*`, or threshold changes are off-limits).
- Do keep secrets and generated artifacts out of git; use `.gitleaks.toml`/`ci_tools/config/*` for safe patterns.
- Do keep required docs current (`README.md`, `CLAUDE.md`, `docs/README.md`, package READMEs) and avoid undoing user edits.

## External Dependencies (DO NOT DELETE)
The following modules are imported by external projects (peak, kalshi, etc.) and must NOT be removed even if they show 0% coverage locally or appear unused:

- `kalshi_ws/` - WebSocket client for Kalshi API (used by peak)
- `rate_limiter.py` - Rate limiting with exponential backoff (used by peak)

These modules may have 0% coverage in common's test suite because they are tested in the consuming projects. Do not delete them based on coverage or unused code analysis.
