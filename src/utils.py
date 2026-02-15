from pathlib import Path
from typing import Union


def create_dist_folder(path: Union[str, Path] = "dist") -> Path:
    """
    Ensure a 'dist' directory exists.

    - Creates the directory (and parents) if necessary.
    - Is idempotent (exists_ok=True).
    - Returns the Path to the directory.
    - Raises RuntimeError on failure (for example if a file exists at the path).
    """
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise RuntimeError(f"Failed to create directory {p!s}: {exc}") from exc

    if not p.exists() or not p.is_dir():
        # This covers the case where a file exists at the path or the path is unusable.
        raise RuntimeError(f"Path {p!s} exists but is not a directory")

    return p