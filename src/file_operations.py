"""File operations for managing markdown articles."""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def validate_article_path(path: str) -> bool:
    """Validate that the article path is safe and doesn't contain directory traversal.

    Args:
        path: The relative path for the article (without extension)

    Returns:
        True if path is valid, False otherwise
    """
    if not path:
        return False

    # Check for directory traversal attempts
    if ".." in path or path.startswith("/") or path.startswith("\\"):
        return False

    # Check for invalid characters
    invalid_chars = ["<", ">", ":", '"', "|", "?", "*"]
    if any(char in path for char in invalid_chars):
        return False

    return True


def write_article(
    pages_dir: Path, path: str, title: str, content: str
) -> Optional[Path]:
    """Write an article to the filesystem with frontmatter.

    Args:
        pages_dir: Base directory for pages
        path: Relative path for the article (without extension)
        title: Article title (for frontmatter)
        content: Article content (markdown)

    Returns:
        Path to the created file, or None if validation failed
    """
    if not validate_article_path(path):
        logger.error(f"Invalid article path: {path}")
        return None

    # Ensure path ends with .md
    if not path.endswith(".md"):
        path = f"{path}.md"

    file_path = pages_dir / path

    # Create parent directories if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create frontmatter
    frontmatter = f'---\ntitle: "{title}"\n---\n\n'
    full_content = frontmatter + content

    # Write file
    try:
        file_path.write_text(full_content, encoding="utf-8")
        logger.info(f"Article written: {file_path}")
        return file_path
    except Exception as exc:
        logger.error(f"Failed to write article {file_path}: {exc}")
        return None


def read_article(pages_dir: Path, path: str) -> Optional[tuple[str, str]]:
    """Read an article from the filesystem.

    Args:
        pages_dir: Base directory for pages
        path: Relative path for the article (without extension)

    Returns:
        Tuple of (title, content) or None if not found
    """
    if not validate_article_path(path):
        logger.error(f"Invalid article path: {path}")
        return None

    # Try with .md extension
    file_path = pages_dir / f"{path}.md"

    if not file_path.exists():
        logger.error(f"Article not found: {file_path}")
        return None

    try:
        content = file_path.read_text(encoding="utf-8")

        # Parse frontmatter
        from src.frontmatter import parse_frontmatter

        metadata, body = parse_frontmatter(content)

        title = metadata.get("title", "") if metadata else ""

        return title, body
    except Exception as exc:
        logger.error(f"Failed to read article {file_path}: {exc}")
        return None


def update_article(
    pages_dir: Path, path: str, title: str, content: str
) -> Optional[Path]:
    """Update an existing article.

    Args:
        pages_dir: Base directory for pages
        path: Relative path for the article (without extension)
        title: Article title (for frontmatter)
        content: Article content (markdown)

    Returns:
        Path to the updated file, or None if validation failed
    """
    # Same as write_article - will overwrite existing file
    return write_article(pages_dir, path, title, content)


def delete_article(pages_dir: Path, path: str) -> bool:
    """Delete an article from the filesystem.

    Args:
        pages_dir: Base directory for pages
        path: Relative path for the article (without extension)

    Returns:
        True if deleted successfully, False otherwise
    """
    if not validate_article_path(path):
        logger.error(f"Invalid article path: {path}")
        return False

    # Try with .md extension
    file_path = pages_dir / f"{path}.md"

    if not file_path.exists():
        logger.error(f"Article not found: {file_path}")
        return False

    try:
        file_path.unlink()
        logger.info(f"Article deleted: {file_path}")
        return True
    except Exception as exc:
        logger.error(f"Failed to delete article {file_path}: {exc}")
        return False
