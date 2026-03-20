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
    working_dir: Union[str, Path],
    pages_dir: Union[str, Path],
    dist_dir: Union[str, Path],
    styles_dir: Union[str, Path],
    settings: Settings,
) -> Path:
    """Load pages from `pages_dir`, render them to HTML files and write into `dist_dir`.

    Each page will be written to <dist_dir>/<rel_path>.html where rel_path is the
    POSIX relative path of the source file without extension (e.g., `de/index`).

    Args:
        working_dir: Working directory to load pages from.
        pages_dir: Directory containing source pages
        dist_dir: Directory to write output files
        styles_dir: Directory containing styles
        settings: Settings object

    Returns the Path to the distribution directory.
    """
    working_dir_p = Path(working_dir)

    pages_dir_p = Path(pages_dir)

    # Clean dist directory before building to avoid stale artifacts
    dist_p = Path(dist_dir)
    if dist_p.exists():
        logger.info(f"Cleaning dist directory: {dist_p.resolve()}")
        shutil.rmtree(dist_p)

    dist_p = create_folder(dist_dir)

    # Compile and copy styles with cache-busting
    css_path = compile_and_copy_styles(styles_dir, dist_dir)

    pages = load_pages(pages_dir_p, working_dir_p)

    if not pages:
        logger.info("No pages found to build")
        return dist_p

    logger.info(f"Found {len(pages)} page(s) to build")

    # Use current working directory for templates when used as a CLI
    template_dir = Path.cwd() / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    article_template = env.get_template("article.html")
    index_template = env.get_template("index.html")

    # Create root index.html using the index template
    root_index = dist_p / "index.html"
    try:
        # css_path already contains absolute path from compile_and_copy_styles
        rendered_html = index_template.render(title="Home", css_path=css_path)
        root_index.write_text(rendered_html, encoding="utf-8")
        logger.info(f"  Created root index: {root_index.resolve()}")
    except Exception as exc:
        logger.warning("Failed to write root index: %s", exc)

    for key, page in pages.items():
        # target path is dist/<key>.html
        target = dist_p.joinpath(f"{key}.html")
        target.parent.mkdir(parents=True, exist_ok=True)

        src_suffix = Path(page.source_path).suffix.lower()

        # Determine if this is an index page
        is_index_page = key.endswith("/index") or key == "index"

        try:
            # Get title from metadata or use fallback
            title = (
                page.metadata.get("title") if isinstance(page.metadata, dict) else None
            )
            if not title:
                # fallback title
                title = key.split("/")[-1]

            # Choose template based on whether it's an index page
            if is_index_page:
                # Use index template for index pages (no content)
                rendered_html = index_template.render(title=title, css_path=css_path)
            elif src_suffix in (".html", ".htm"):
                # For non-index HTML files, copy verbatim
                shutil.copyfile(page.source_path, str(target))
                logger.info(
                    f"  {Path(page.source_path).resolve()} -> {target.resolve()}"
                )
                continue
            else:
                # Use post template for markdown pages
                rendered_html = article_template.render(
                    title=title, content=page.html, css_path=css_path
                )

            target.write_text(rendered_html, encoding="utf-8")
            logger.info(f"  {Path(page.source_path).resolve()} -> {target.resolve()}")
        except Exception as exc:
            logger.warning(
                "Failed to write page %s -> %s: %s",
                Path(page.source_path).resolve(),
                target.resolve(),
                exc,
            )

    return dist_p
