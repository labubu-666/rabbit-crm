# rabbit

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
