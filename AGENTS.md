# Coding
- Prefer simple solutions to complicated ones.
- Only do what was asked, dont wander off into tangents.
# Dependencies
- The project uses `uv`.
# Development
## Working directory
Override working directory using `--working-dir`.
## Build
- `uv run build` builds pages and puts them in `./dist`.
## Serve
- `uv run rabbit serve --dev` no need to restart the server, it has live reloaded.
# Linting
## pre-commit
- Manages git commit hooks installed via `pre-commit install`.
- `pre-commit install` has to be run again after any changes to `.pre-commit-config.yaml`.
## ruff
- After making changes, run `uv run ruff format` to make sure files are correctly linted.
# Testing
- The project exclusively uses `pytest`.
- Prefer `monkeypatch` to `unittest.mock.patch`.
- Run tests using `uv run pytest -vvv`.
