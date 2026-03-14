FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

COPY pyproject.toml pyproject.toml
COPY README.md README.md

RUN uv sync

ENTRYPOINT ["uv", "run", "--directory", "integration-tests/wiki", "rabbit", "serve", "--host", "0.0.0.0"]