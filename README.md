# rabbit-crm

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

# Quick start

## Install

    uv add git+ssh://git@github.com/labubu-666/rabbit.git@main

## Serve

### By default , served from current directory
    uv run rabbit serve

### Specify directory with
    uv run --directory integration-tests/knowledge-bases/hello-world rabbit serve

# Dev

## Build natively

    uv run rabbit build

## Install

    uv add git+ssh://git@github.com/labubu-666/rabbit.git@main

# Publish to PyPI

## Build package

    python -m build

## Upload to PyPI

    twine check dist/*

    TWINE_USERNAME= TWINE_PASSWORD= twine upload dist/*
