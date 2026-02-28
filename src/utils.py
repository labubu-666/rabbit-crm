import logging
import subprocess

from pathlib import Path
from typing import Union, Dict, Tuple

import yaml
import shutil
from jinja2 import Environment, FileSystemLoader, select_autoescape
from checksumdir import dirhash

from src.markdown import _render_markdown
from src.schema import Page, Frontmatter

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
            raise ValueError(f"Frontmatter must be a YAML dict, got {type(metadata).__name__}")
        
        # Validate using Pydantic Frontmatter model (validates title field exists)
        Frontmatter(**metadata)
        
    except Exception as exc:
        logger.warning("Failed to parse YAML frontmatter: %s", exc)
        raise

    return metadata, rest


def load_pages(path: Union[str, Path] = "pages") -> Dict[str, Page]:
    """Recursively load markdown pages from `path`, parse frontmatter and render HTML.

    Returns a dict mapping POSIX relative paths (without extension) to `Page` models.
    Example: pages/de/index.md -> key 'de/index'
    """
    pages_dir = Path(path)
    if not pages_dir.exists() or not pages_dir.is_dir():
        logger.info(
            "Pages directory %s does not exist; returning empty dict", pages_dir.resolve()
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
        The relative path to the CSS file (e.g., 'styles/index.f522ae8f.css'), or None if styles don't exist
    """
    styles_dir_p = Path(styles_dir)
    dist_p = Path(dist_dir)
    
    if not styles_dir_p.exists():
        logger.warning(f"Styles directory {styles_dir_p.resolve()} does not exist, skipping styles compilation")
        return None
    
    # Create styles subdirectory in dist
    dist_styles_p = dist_p / "styles"
    dist_styles_p.mkdir(parents=True, exist_ok=True)
    
    # Compile SCSS to CSS using subprocess
    scss_input = styles_dir_p / "index.scss"
    css_output = styles_dir_p / "index.css"
    
    if not scss_input.exists():
        logger.warning(f"SCSS file {scss_input.resolve()} does not exist, skipping styles compilation")
        return None
    
    try:
        # Run sass command using subprocess
        logger.info(f"Compiling SCSS: {scss_input.resolve()} -> {css_output.resolve()}")
        result = subprocess.run(
            ["sass", str(scss_input), str(css_output)],
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout:
            logger.debug(f"sass stdout: {result.stdout}")
        logger.info(f"SCSS compilation successful")
    except subprocess.CalledProcessError as exc:
        logger.error(f"SCSS compilation failed: {exc.stderr}")
        raise
    except FileNotFoundError:
        logger.error("sass command not found. Please install sass (e.g., 'npm install -g sass')")
        raise
    
    # Generate hash for cache busting
    try:
        styles_hash = dirhash(str(styles_dir_p), 'md5', excluded_files=['.gitignore'])
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
        logger.error(f"CSS file {css_output.resolve()} does not exist after compilation!")
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
    return f"styles/{css_filename}"


def build_site(
    pages_dir: Union[str, Path] = "pages", 
    dist_dir: Union[str, Path] = "dist",
    styles_dir: Union[str, Path] = "styles"
) -> Path:
    """Load pages from `pages_dir`, render them to HTML files and write into `dist_dir`.

    Each page will be written to <dist_dir>/<rel_path>.html where rel_path is the
    POSIX relative path of the source file without extension (e.g., `de/index`).

    Args:
        pages_dir: Directory containing source pages
        dist_dir: Directory to write output files
        styles_dir: Directory containing styles

    Returns the Path to the distribution directory.
    """
    pages_dir_p = Path(pages_dir)
    dist_p = Path(dist_dir)
    
    dist_p = create_dist_folder(dist_dir)

    # Compile and copy styles with cache-busting
    css_path = compile_and_copy_styles(styles_dir, dist_dir)

    pages = load_pages(pages_dir_p)
    
    if not pages:
        logger.info("No pages found to build")
        return dist_p
    
    logger.info(f"Found {len(pages)} page(s) to build")
    
    # Use current working directory for templates when used as a CLI
    template_dir = Path.cwd() / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template("template.html")

    for key, page in pages.items():
        # target path is dist/<key>.html
        target = dist_p.joinpath(f"{key}.html")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Always make the site root (index) a redirect to the German index
        # This ensures that visiting / will land on /de/index.html
        if key == "index":
            redirect_html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=de/index.html">
  <meta name="robots" content="noindex">
  <link rel="canonical" href="de/index.html">
  <title>Redirecting...</title>
  <script>window.location.replace('de/index.html');</script>
</head>
<body>
  Redirecting to <a href="de/index.html">de/index.html</a>.
</body>
</html>
"""

            try:
                target.write_text(redirect_html, encoding="utf-8")
                logger.info(f"  {Path(page.source_path).resolve()} -> {target.resolve()} (redirect)")
            except Exception as exc:
                logger.warning(
                    "Failed to write redirect %s -> %s: %s",
                    Path(page.source_path).resolve(),
                    target.resolve(),
                    exc,
                )
            # skip the normal write/copy logic for the index page
            continue

        src_suffix = Path(page.source_path).suffix.lower()
        try:
            if src_suffix in (".html", ".htm"):
                # copy HTML file verbatim
                shutil.copyfile(page.source_path, str(target))
                logger.info(f"  {Path(page.source_path).resolve()} -> {target.resolve()}")
            else:
                title = (
                    page.metadata.get("title")
                    if isinstance(page.metadata, dict)
                    else None
                )
                if not title:
                    # fallback title
                    title = key.split("/")[-1]

                # Calculate relative path to CSS from this page
                # For pages in subdirectories, we need to go up levels
                # Only calculate css_rel_path if css_path exists
                if css_path:
                    depth = len(Path(key).parts) - 1
                    css_rel_path = "../" * depth + css_path if depth > 0 else css_path
                else:
                    css_rel_path = None

                # Render using Jinja2 template
                rendered_html = template.render(
                    title=title, 
                    content=page.html,
                    css_path=css_rel_path
                )
                target.write_text(rendered_html, encoding="utf-8")
                logger.info(f"  {Path(page.source_path).resolve()} -> {target.resolve()}")
        except Exception as exc:
            logger.warning(
                "Failed to write page %s -> %s: %s", Path(page.source_path).resolve(), target.resolve(), exc
            )

    return dist_p
