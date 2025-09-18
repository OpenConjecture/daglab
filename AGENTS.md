# Repository Guidelines

## Project Structure & Module Organization
Source lives under `src/daglab`, organized by concern (`runtime`, `helpers`, `templates`, `cli.py`). Tests mirror packages in `tests/unit` and scenario coverage in `tests/integration`. Keep docs in `docs/` and runnable walkthroughs in `examples/`. Shared coordination artifacts and agent memory live in `coordination/` and `memory/`; avoid hard-coding paths outside these directories. Global configuration defaults sit in `daglab.yaml` and `config/`.

## Build, Test, and Development Commands
- `pip install -e ".[dev]"` sets up the editable package with dev tooling.
- `daglab doctor` validates local dependencies before running notebooks or Dagster assets.
- `pytest` (or `pytest tests/unit`) runs the full suite; add `--cov=daglab` to inspect coverage reports in `htmlcov/`.
- `mypy src/daglab` and `ruff check src/daglab` enforce static typing and linting; use `ruff format src/daglab` for formatting.
- `pre-commit run --all-files` mirrors CI checks locally.

## Coding Style & Naming Conventions
Python 3.9+ is required. Format with Black (line length 100) and keep imports sorted per Ruff’s isort rules. Write functions and modules with descriptive snake_case names; classes remain PascalCase. Type hints are mandatory—CI treats `disallow_untyped_defs` as strict. Prefer dependency injection of paths/config instead of globals so notebooks remain reproducible.

## Testing Guidelines
Author tests in `tests/unit/<module>` mirroring the import path, naming files `test_<feature>.py`. Integration workflows belong in `tests/integration/` and may use `@pytest.mark.integration`. Maintain ≥80% coverage (`--cov-fail-under=80`). Slow scenarios should use the `slow` marker; document any new fixtures on discovery in `tests/conftest.py`.

## Commit & Pull Request Guidelines
Follow the existing history: short, capitalized imperative subject lines (`Add Config Loader`, `Fix Template Watcher`). Keep commits scoped to one logical change with relevant tests updated. Pull requests must include a summary, linked issues (e.g., `Closes #123`), and validation notes (tests or manual runs). Attach screenshots or CLI transcripts when behavior or UX changes. Request at least one review before merging.

## Configuration Tips
Respect the precedence chain (CLI args → env vars `DAGLAB_*` → `daglab.yaml`). Never commit secrets; use `.env` locally and document required keys in `docs/`. When introducing new settings, update `config/schema.py` (or the relevant Pydantic model) and provide defaults that keep `daglab doctor` passing.
