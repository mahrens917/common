# Repository Guidelines

## Project Structure & Module Organization

- `src/common/`: main library code (src-layout package; import as `common.*`).
- `tests/`: `pytest` test suite (unit tests live under `tests/unit/`).
- `scripts/`: developer/CI entrypoints (notably `scripts/ci.sh`).
- `config/`, `pyproject.toml`: runtime/config + tool configuration.

## Build, Test, and Development Commands

- `make check` / `./scripts/ci.sh`: run the shared CI pipeline via `~/ci_shared`.
- `python -m ci_tools.ci --model gpt-5-codex`: run the shared CI driver directly.
- `make format`: auto-format with `isort` (Black profile) and `black`.
- `make lint`: `compileall` + `pylint` (`--errors-only`).
- `make type`: run `pyright` on `src/`.
- `pytest tests/ --cov=src --cov-fail-under=80 --strict-markers -W error`: tests + coverage gate.

## Coding Style & Naming Conventions

- Python 3.12+.
- Formatting: Black + isort; do not hand-format.
- Linting: Ruff is enforced in CI; prefer explicit exception types.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Avoid weakening checks (`# noqa`, `# pylint: disable`, `# type: ignore`, guard allowlists).
- Prefer config files over new environment variables; document required ENV.

## Testing Guidelines

- Framework: `pytest` (with async support via `pytest-asyncio`).
- Place new tests near the code they cover: `tests/unit/<module_path>/test_<name>.py`.
- Keep tests deterministic (avoid real network/Redis; use fakes/fixtures/mocking).

## CI Pipeline & Guardrails

- Order (high level): spelling/unused/deps/security → `ruff` → `pyright` → `pylint` → `pytest` → coverage/bytecode checks.
- Guardrails: functions ≤80 lines; modules ≤400; cyclomatic ≤10 / cognitive ≤15; avoid broad/empty exception handlers and literal fallbacks (`.get`, `setdefault`, ternaries, `os.getenv`, `if x is None`); avoid `time.sleep`/`subprocess.*`/`requests.*` in `src/`.

## Duplicate Code Rule

- Search before adding helpers: `rg "def <name>" src/common`.
- If duplication exists, centralize the best implementation in `src/common/` and update callers to import it.

## Commit & Pull Request Guidelines

- Commit messages in history are short, imperative, and descriptive (e.g., “Fix …”, “Add …”, “Remove …”).
- PRs should include: a clear summary, rationale, and any relevant test output (at least `./scripts/ci.sh`).
- If behavior changes, add/adjust tests and ensure coverage stays above the threshold.

## Security & Configuration Tips

- CI runs `gitleaks`; do not commit secrets (API keys, tokens, private URLs).
- Shared tooling is expected at `~/ci_shared`; override with `CI_SHARED_ROOT=/path/to/ci_shared`.
