# rabbit-crm

[![](https://img.shields.io/pypi/v/rabbit-crm.svg)](https://pypi.org/project/rabbit-crm/) [![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

# Quick start

## Install
    pip install rabbit-crm

## Serve

### By default , served from current directory
    uv run rabbit-crm serve

### Specify directory with
    uv run rabbit-crm serve --working-dir integration-tests/knowledge-bases/hello-world

# Dev

## Run with

    uv run rabbit-crm serve --working-dir integration-tests/knowledge-bases/hello-world --dev

## Remote install from git branch

    uv add git+ssh://git@github.com/labubu-666/rabbit-crm.git@main

# Publish to PyPI

## Build package

    python -m build

## Upload to PyPI

    twine check dist/*

    TWINE_USERNAME=__token__ TWINE_PASSWORD=foobar twine upload dist/*

## Trigger deploy on CD

    git push --tags
