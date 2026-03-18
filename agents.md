# Dependencies
- The project uses `uv`.
# Development server
- `uv run rabbit serve` no need to restart the server, it has live reload.
# Linting
## pre-commit
- Manages git commit hooks installed via `pre-commit install`.
- `pre-commit install` has to be run again after any changes to `.pre-commit-config.yaml`.
## ruff
- After making changes, run `uv run ruff format` to make sure files are correctly linted.
# Testing
- The project exclusively uses `pytest`.
- Run using `uv run pytest -vvv`.
