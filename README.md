# rabbit-crm

[![](https://img.shields.io/pypi/v/rabbit-crm.svg)](https://pypi.org/pypi/name/) [![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

# Quick start

## Install
    pip install rabbit-crm

## Serve

### By default , served from current directory
    uv run rabbit serve

### Specify directory with
    uv run --directory integration-tests/knowledge-bases/hello-world rabbit serve

# Dev

## Build natively

    uv run rabbit build

## Remote install from git branch

    uv add git+ssh://git@github.com/labubu-666/rabbit.git@main

# Publish to PyPI

## Build package

    python -m build

## Upload to PyPI

    twine check dist/*

    TWINE_USERNAME=__token__ TWINE_PASSWORD=foobar twine upload dist/*

## Trigger deploy on CD

    git push --tags
