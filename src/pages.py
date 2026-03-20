import logging
import subprocess

from pathlib import Path
from typing import Union, Dict
import shutil
from checksumdir import dirhash

from frontmatter import parse_frontmatter
from src.markdown import _render_markdown
from src.schema import Page

logger = logging.getLogger(__name__)


def load_pages(path: Path = "pages", working_dir: Path = ".") -> Dict[str, Page]:
    """Recursively load markdown pages from `path`, parse frontmatter and render HTML.

    Args:
        path: Directory containing markdown pages
        working_dir: Working directory to use for plugin discovery in markdown rendering

    Returns a dict mapping POSIX relative paths (without extension) to `Page` models.
    Example: pages/de/index.md -> key 'de/index'
    """
    pages_dir = Path(path)
    if not pages_dir.exists() or not pages_dir.is_dir():
        logger.info(
            "Pages directory '%s' does not exist.",
            pages_dir.resolve(),
        )
        return {}

    result: Dict[str, Page] = {}

    patterns = ("*.md", "*.markdown", "*.html", "*.htm")
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
                logger.warning("Failed to read %s: %s", fp.resolve(), exc)
                continue

            # If the file is an HTML file, do not attempt to parse frontmatter
            # or render it as markdown — treat the content as already-rendered HTML
            if fp.suffix.lower() in (".html", ".htm"):
                metadata = {}
                content = raw
                html = raw
            else:
                metadata, content = parse_frontmatter(raw)
                html = _render_markdown(content, working_dir=working_dir)

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
                logger.warning(
                    "Duplicate page key %s - %s will override previous %s",
                    key,
                    Path(page.source_path).resolve(),
                    Path(result[key].source_path).resolve(),
                )

            result[key] = page

    return result


def compile_and_copy_styles(
    styles_dir: Union[str, Path] = "styles", dist_dir: Union[str, Path] = "dist"
) -> str:
    """Compile SCSS to CSS using subprocess and copy to dist with cache-busting hash.

    Args:
        styles_dir: Directory containing SCSS files
        dist_dir: Directory to write output CSS files

    Returns:
        The absolute path to the CSS file (e.g., '/assets/styles/index.f522ae8f.css'), or None if styles don't exist
    """
    styles_dir_p = Path(styles_dir)
    dist_p = Path(dist_dir)

    if not styles_dir_p.exists():
        logger.warning(
            f"Styles directory {styles_dir_p.resolve()} does not exist, skipping styles compilation"
        )
        return None

    # Create assets/styles subdirectory in dist
    dist_styles_p = dist_p / "assets" / "styles"
    dist_styles_p.mkdir(parents=True, exist_ok=True)

    # Compile SCSS to CSS using subprocess
    scss_input = styles_dir_p / "index.scss"
    css_output = styles_dir_p / "index.css"

    if not scss_input.exists():
        logger.warning(
            f"SCSS file {scss_input.resolve()} does not exist, skipping styles compilation"
        )
        return None

    try:
        # Run sass command using subprocess
        logger.info(f"Compiling SCSS: {scss_input.resolve()} -> {css_output.resolve()}")
        result = subprocess.run(
            ["sass", str(scss_input), str(css_output)],
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout:
            logger.debug(f"sass stdout: {result.stdout}")
        logger.info("SCSS compilation successful")
    except subprocess.CalledProcessError as exc:
        logger.error(f"SCSS compilation failed: {exc.stderr}")
        raise
    except FileNotFoundError:
        logger.error(
            "sass command not found. Please install sass (e.g., 'npm install -g sass')"
        )
        raise

    # Generate hash for cache busting
    try:
        styles_hash = dirhash(str(styles_dir_p), "md5", excluded_files=[".gitignore"])
        # Use first 8 characters of hash for brevity
        hash_suffix = styles_hash[:8]
        logger.info(f"Generated styles hash: {hash_suffix}")
    except Exception as exc:
        logger.warning(f"Failed to generate hash for styles: {exc}, using timestamp")
        import time

        hash_suffix = str(int(time.time()))

    # Copy CSS to dist with hash suffix
    css_filename = f"index.{hash_suffix}.css"
    css_dest = dist_styles_p / css_filename

    # Verify source file exists before copying
    if not css_output.exists():
        logger.error(
            f"CSS file {css_output.resolve()} does not exist after compilation!"
        )
        raise FileNotFoundError(f"CSS file {css_output.resolve()} not found")

    try:
        shutil.copyfile(str(css_output), str(css_dest))
        logger.info(f"Copied styles: {css_output.resolve()} -> {css_dest.resolve()}")

        # Verify the file was actually copied
        if not css_dest.exists():
            logger.error(f"CSS file was not copied to {css_dest.resolve()}!")
            raise RuntimeError(f"Failed to copy CSS to {css_dest.resolve()}")

        logger.info(f"Verified CSS file exists at: {css_dest.resolve()}")
    except Exception as exc:
        logger.error(f"Failed to copy CSS file: {exc}")
        raise

    # Return relative path to CSS file for use in templates
    return f"/assets/styles/{css_filename}"
