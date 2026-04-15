import logging
import shutil
from pathlib import Path
from typing import Union


from pages import compile_and_copy_styles, load_pages
from settings import Settings
from src.utils.file_manager import create_folder
from src.search import rebuild_search_index

logger = logging.getLogger(__name__)


def build_site(
    working_dir: Union[str, Path],
    pages_dir: Union[str, Path],
    dist_dir: Union[str, Path],
    styles_dir: Union[str, Path],
    settings: Settings,
) -> Path:
    """Build static assets (styles) only. Pages are served from memory.

    Args:
        working_dir: Working directory to load pages from.
        pages_dir: Directory containing source pages (used for validation)
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
    logger.info("Building assets (styles only)...")
    css_path = compile_and_copy_styles(styles_dir, dist_dir)

    if css_path:
        logger.info(f"Assets built successfully: {css_path}")
    else:
        logger.info("No styles to build")

    # Load pages to verify they can be loaded (but don't write HTML)
    pages = load_pages(pages_dir_p, working_dir_p)

    if not pages:
        logger.info("No pages found")
    else:
        logger.info(f"Found {len(pages)} page(s) (will be served from memory)")

    # Rebuild search index with loaded pages
    if pages:
        logger.info("Building search index...")
        rebuild_search_index(pages)
        logger.info("Search index built successfully")

    return dist_p
