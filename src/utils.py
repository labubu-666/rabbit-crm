import logging
import re
import html as html_module

from pathlib import Path
from typing import Union, Dict, Tuple

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def create_folder(path: Union[str, Path]) -> Path:
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise RuntimeError(f"Failed to create directory {p!s}: {exc}") from exc

    if not p.exists() or not p.is_dir():
        # This covers the case where a file exists at the path or the path is unusable.
        raise RuntimeError(f"Path {p!s} exists but is not a directory")

    return p

def create_dist_folder(path: Union[str, Path] = "dist") -> Path:
    p = create_folder("dist")

    return p

class Page(BaseModel):
    metadata: dict = Field(default_factory=dict)
    content: str = ""
    html: str = ""
    # helpful fields for consumers
    source_path: str = ""
    rel_path: str = ""


def _parse_frontmatter(text: str) -> Tuple[dict, str]:
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
            # Ensure a dict for consistency
            metadata = {"_frontmatter": metadata}
    except Exception as exc:  # keep parsing robust
        logger.warning("Failed to parse YAML frontmatter: %s", exc)
        metadata = {"_frontmatter_error": str(exc)}


    return metadata, rest


def _render_markdown(md_text: str) -> str:
    # Minimal fallback renderer: escape HTML, convert headings, links, and paragraphs
    text = html_module.escape(md_text)

    # headings
    def _repl_h(m):
        level = len(m.group(1))
        content = m.group(2).strip()
        return f"<h{level}>{content}</h{level}>"

    text = re.sub(r'^(#{1,6})\s+(.*)$', _repl_h, text, flags=re.M)

    # links [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f"<a href=\"{html_module.escape(m.group(2))}\">{m.group(1)}</a>", text)

    # paragraphs: split on two or more newlines
    parts = re.split(r"\n\s*\n", text.strip())
    parts = [p.replace('\n', '<br/>') for p in parts if p.strip()]
    html = "".join(f"<p>{p}</p>" for p in parts)

    return html


def load_pages(path: Union[str, Path] = "pages") -> Dict[str, Page]:
    """Recursively load markdown pages from `path`, parse frontmatter and render HTML.

    Returns a dict mapping POSIX relative paths (without extension) to `Page` models.
    Example: pages/de/index.md -> key 'de/index'
    """
    pages_dir = Path(path)
    if not pages_dir.exists() or not pages_dir.is_dir():
        logger.info("Pages directory %s does not exist; returning empty dict", pages_dir)
        return {}

    result: Dict[str, Page] = {}

    patterns = ("*.md", "*.markdown")
    for pattern in patterns:
        for fp in pages_dir.rglob(pattern):
            # skip hidden files and directories
            try:
                rel_parts = fp.relative_to(pages_dir).parts
            except Exception:
                # shouldn't happen but be robust
                rel_parts = fp.parts

            if any(part.startswith(".") for part in rel_parts):
                continue

            try:
                raw = fp.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                logger.warning("Failed to read %s: %s", fp, exc)
                continue

            metadata, content = _parse_frontmatter(raw)
            html = _render_markdown(content)

            rel_path = fp.relative_to(pages_dir).with_suffix("")
            key = rel_path.as_posix()

            page = Page(
                metadata=metadata or {},
                content=content,
                html=html,
                source_path=str(fp),
                rel_path=key,
            )

            if key in result:
                logger.warning("Duplicate page key %s - %s will override previous %s", key, page.source_path, result[key].source_path)

            result[key] = page

    return result


def build_site(pages_dir: Union[str, Path] = "pages", dist_dir: Union[str, Path] = "dist") -> Path:
    """Load pages from `pages_dir`, render them to HTML files and write into `dist_dir`.

    Each page will be written to <dist_dir>/<rel_path>.html where rel_path is the
    POSIX relative path of the source file without extension (e.g., `de/index`).

    Returns the Path to the distribution directory.
    """
    pages_dir_p = Path(pages_dir)
    dist_p = create_dist_folder(dist_dir)

    pages = load_pages(pages_dir_p)

    for key, page in pages.items():
        # target path is dist/<key>.html
        target = dist_p.joinpath(f"{key}.html")
        target.parent.mkdir(parents=True, exist_ok=True)

        title = page.metadata.get("title") if isinstance(page.metadata, dict) else None
        if not title:
            # fallback title
            title = key.split("/")[-1]

        full_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html_module.escape(str(title))}</title>
</head>
<body>
{page.html}
</body>
</html>
"""

        try:
            target.write_text(full_html, encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to write page %s -> %s: %s", page.source_path, target, exc)

    return dist_p

