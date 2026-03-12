# Common: Claude Guide

Shared Python utilities library used across multiple trading system repositories. Code lives in `src/common/`, tests mirror the layout in `tests/`.

## Path Portability
- All repos live as siblings under `~/projects/` (e.g., `~/projects/monitor`, `~/projects/common`).
- NEVER hardcode absolute paths like `/Users/<username>/projects/...` in code or config.
- Use `~/projects/<repo>` in config files; code must call `Path.expanduser()` when resolving these paths.
- Cross-repo `file://` URIs in `pyproject.toml` are for local dev only; EC2 installs via `~/projects/monitor/scripts/deploy/install_local_packages.sh`.

## Quick Commands
- Run CI/automation with `make check` or `python -m ci_tools.ci --model claude-sonnet-4-6` (delegates to `scripts/ci.sh` through `ci_shared.mk`).
- Tests: `pytest tests/ --cov=src --cov-fail-under=80 --strict-markers --cov-report=term -W error` (serial execution). Coverage guard enforces 80%.
- Formatting/type/lint: `make format`, `make type`, `make lint`.

## Code Hygiene
- Avoid adding fallbacks, duplicate code, or backward-compatibility shims (backward compatibility is not required); call out and fix fail-fast gaps or dead code when encountered.
- Prefer config JSON files over new environment variables; only add ENV when required and document it.

## Duplicate Code Rule
- Search `src/common/` before adding helpers (`rg "def <name>" src`). Many utilities already exist.
- If a duplicate surfaces, centralize the best version, update callers to import it, and document the delegation.

## CI Pipeline (exact order)
- `codespell` -> `vulture` -> `deptry` -> `gitleaks` -> `bandit_wrapper` -> `safety scan` (skipped with `CI_AUTOMATION`) -> `ruff --fix` -> `pyright --warnings` -> `pylint` -> `pytest` -> `coverage_guard` -> `compileall`.
- Limits: classes ≤150 lines; functions ≤80; modules ≤600; cyclomatic ≤10 / cognitive ≤15; inheritance depth ≤2; ≤15 public / 30 total methods; ≤8 instantiations in `__init__`/`__post_init__`; `unused_module_guard --strict`; `delegation_guard` (no module-scope setattr, no single-method wrappers, no pass-through functions, no empty helper packages); `fragmentation_guard` (packages with ≥2 modules must not have ≥50% under 40 significant lines); documentation guard requires README/CLAUDE/docs hierarchy.
- Policy guard reminders: banned tokens (`legacy`, `fallback`, `default`, `catch_all`, `failover`, `backup`, `compat`, `backwards`, `deprecated`, `legacy_mode`, `old_api`, `legacy_flag`, TODO/FIXME/HACK/WORKAROUND), no broad/empty exception handlers, no literal fallbacks in `.get`/`setdefault`/ternaries/`os.getenv`/`if x is None`, and no `time.sleep`/`subprocess.*`/`requests.*` inside `src`.
- Prep: `tool_config_guard --sync` runs up front; PYTHONPATH is set to include `~/projects/ci_shared`.

## CI Workflow
- `ruff --fix` runs during CI and modifies files in-place. Always commit or stash changes before running `make check` to avoid losing work.
  1. Make changes
  2. Let ruff auto-fix trivial issues (`--fix`)
  3. Review and commit

## Do/Don't
- Do fix the code rather than weakening checks (`# noqa`, `# pylint: disable`, `# type: ignore`, `policy_guard: allow-*`, or threshold changes are off-limits).
- Do keep secrets and generated artifacts out of git; use `.gitleaks.toml`/`ci_tools/config/*` for safe patterns.
- Do keep required docs current (`README.md`, `CLAUDE.md`, `docs/README.md`, package READMEs) and avoid undoing user edits.

## External Dependencies (DO NOT DELETE)
The following modules are imported by external projects (peak, kalshi, etc.) and must NOT be removed even if they show 0% coverage locally or appear unused:

- `kalshi_ws/` - WebSocket client for Kalshi API (used by peak)
- `rate_limiter.py` - Rate limiting with exponential backoff (used by peak)

These modules may have 0% coverage in common's test suite because they are tested in the consuming projects. Do not delete them based on coverage or unused code analysis.
