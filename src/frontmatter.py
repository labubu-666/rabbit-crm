from typing import Tuple

import logging

import yaml

from src.schema import Frontmatter

logger = logging.getLogger(__name__)


def parse_frontmatter(text: str) -> Tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text

    # split lines and look for closing '---' on its own line
    lines = text.splitlines(True)
    if len(lines) < 2:
        return {}, text

    # first line is '---'
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        # no closing delimiter -> treat as no frontmatter
        return {}, text

    front = "".join(lines[1:end_idx])
    rest = "".join(lines[end_idx + 1 :])

    try:
        metadata = yaml.safe_load(front) or {}
        if not isinstance(metadata, dict):
            raise ValueError(
                f"Frontmatter must be a YAML dict, got {type(metadata).__name__}"
            )

        # Validate using Pydantic Frontmatter model (validates title field exists)
        Frontmatter(**metadata)

    except Exception as exc:
        logger.warning("Failed to parse YAML frontmatter: %s", exc)
        raise

    return metadata, rest
