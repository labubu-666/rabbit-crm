# rabbit

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

# Quick start

    uv add git+ssh://git@github.com/labubu-666/rabbit.git@main

# Dev

    docker compose up

# Build natively

    uv run rabbit build

# Serve

## By default , served from current directory
    uv run rabbit serve

## Specify directory with
    uv run --directory integration-tests/knowledge-bases/hello-world rabbit serve
