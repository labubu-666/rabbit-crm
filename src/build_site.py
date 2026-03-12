import logging
import shutil
from pathlib import Path
from typing import Union

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pages import compile_and_copy_styles, load_pages
from settings import Settings
from src.utils.file_manager import create_folder

logger = logging.getLogger(__name__)

def build_site(
        pages_dir: Union[str, Path],
        dist_dir: Union[str, Path],
        styles_dir: Union[str, Path],
        settings: Settings
) -> Path:
    """Load pages from `pages_dir`, render them to HTML files and write into `dist_dir`.

    Each page will be written to <dist_dir>/<rel_path>.html where rel_path is the
    POSIX relative path of the source file without extension (e.g., `de/index`).

    Args:
        pages_dir: Directory containing source pages
        dist_dir: Directory to write output files
        styles_dir: Directory containing styles
        settings: Settings object

    Returns the Path to the distribution directory.
    """
    pages_dir_p = Path(pages_dir)

    dist_p = create_folder(dist_dir)

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

    # Create root index.html redirect (without needing a source file)
    root_index = dist_p / "index.html"
    redirect_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=/web/{settings.language_code}/index.html">
  <meta name="robots" content="noindex">
  <link rel="canonical" href="/web/{settings.language_code}/index.html">
  <title>Redirecting...</title>
  <script>window.location.replace('/web/{settings.language_code}/index.html');</script>
</head>
<body>
  Redirecting to <a href="/web/{settings.language_code}/index.html">{settings.language_code}/index.html</a>.
</body>
</html>
"""
    try:
        root_index.write_text(redirect_html, encoding="utf-8")
        logger.info(f"  Created root redirect: {root_index.resolve()}")
    except Exception as exc:
        logger.warning("Failed to write root index redirect: %s", exc)

    for key, page in pages.items():
        # target path is dist/<key>.html
        target = dist_p.joinpath(f"{key}.html")
        target.parent.mkdir(parents=True, exist_ok=True)

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
