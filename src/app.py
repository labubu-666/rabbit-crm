from fastapi import FastAPI, Query, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager
import logging

from starlette.responses import Response, FileResponse, RedirectResponse, HTMLResponse

from src.search import get_search_index, rebuild_search_index
from src.schema import Article
from src.pages import compile_and_copy_styles
from src import __version__

logger = logging.getLogger(__name__)


class PaginationResponse(BaseModel):
    results: list
    offset: int
    limit: int
    count: int


dist_path = Path("dist")

DEFAULT_PAGINATION_SIZE = 25


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup and shutdown."""
    # Startup: Load pages and build search index
    if hasattr(app.state, "pages_dir") and hasattr(app.state, "working_dir"):
        from src.pages import load_pages

        pages_dir = Path(app.state.pages_dir)
        working_dir = Path(app.state.working_dir)
        styles_dir = working_dir / "styles"

        logger.info("Loading pages for search index...")
        pages = load_pages(pages_dir, working_dir)
        logger.info(f"Loaded {len(pages)} page(s)")

        # Store pages in app state for API access
        app.state.pages = pages

        # Compile and copy styles with cache-busting
        logger.info("Compiling styles...")
        css_path = compile_and_copy_styles(styles_dir, dist_path)
        app.state.css_path = css_path
        logger.info(f"Styles compiled: {css_path}")

        # Setup Jinja2 templates
        templates_dir = working_dir / "templates"
        app.state.templates = Jinja2Templates(directory=str(templates_dir))
        logger.info(f"Templates loaded from: {templates_dir}")

        logger.info("Building search index...")
        rebuild_search_index(pages)
        logger.info("Search index built successfully")

    yield

    logger.info("Shutting down app...")


app = FastAPI(
    docs_url="/api/docs", title="rabbit", version=__version__, lifespan=lifespan
)


@app.get("/api/v1/version")
async def version():
    return {"version": __version__}


@app.get("/api/v1/search", response_model=PaginationResponse)
async def search(
    q: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(
        DEFAULT_PAGINATION_SIZE, ge=1, le=100, description="Maximum number of results"
    ),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
    """Search through indexed pages using trigram matching."""
    if not q:
        return PaginationResponse(results=[], offset=offset, limit=limit, count=0)

    search_index = get_search_index()
    result = search_index.search(q, limit=limit, offset=offset)

    return PaginationResponse(**result)


@app.get("/api/v1/articles", response_model=PaginationResponse)
async def list_articles(
    limit: int = Query(
        DEFAULT_PAGINATION_SIZE, ge=1, le=100, description="Maximum number of results"
    ),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
    """List all articles with pagination support."""
    pages = getattr(app.state, "pages", {})

    # Convert pages to articles, filtering out index pages
    articles = []
    for key, page in pages.items():
        # Skip index pages
        if key.endswith("/index") or key == "index":
            continue

        # Get title from metadata or use fallback
        title = page.metadata.get("title") if isinstance(page.metadata, dict) else None
        if not title:
            # Use the last part of the path as fallback
            title = key.split("/")[-1].replace("-", " ").title()

        article: Article = {
            "title": title,
            "path": key,
        }
        articles.append(article)

    # Sort articles by title
    articles.sort(key=lambda x: x["title"])

    # Apply pagination
    total_count = len(articles)
    paginated_articles = articles[offset : offset + limit]

    return PaginationResponse(
        results=paginated_articles,
        offset=offset,
        limit=limit,
        count=total_count,
    )


@app.get("/web/{path:path}")
async def serve_web(path: str):
    """Serve files from the dist directory with .html extension fallback."""
    if not path:
        path = "index"

    file_path = dist_path / path

    # If the path exists as-is, serve it
    if file_path.is_file():
        return FileResponse(file_path)

    # Try adding .html extension
    html_path = dist_path / f"{path}.html"
    if html_path.is_file():
        return FileResponse(html_path)

    # Check for index.html in directory
    if file_path.is_dir():
        index_path = file_path / "index.html"
        if index_path.is_file():
            return FileResponse(index_path)

    return Response(content="Not Found", status_code=404)


@app.get("/web", response_class=HTMLResponse)
async def serve_web_root(
    request: Request,
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(
        DEFAULT_PAGINATION_SIZE, ge=1, le=100, description="Maximum number of results"
    ),
):
    """Serve index page dynamically with pagination."""
    templates = getattr(app.state, "templates", None)
    css_path = getattr(app.state, "css_path", None)

    pages = getattr(app.state, "pages", {})

    # Convert pages to articles, filtering out index pages
    articles = []
    for key, page_obj in pages.items():
        # Skip index pages
        if key.endswith("/index") or key == "index":
            continue

        # Get title from metadata or use fallback
        title = (
            page_obj.metadata.get("title")
            if isinstance(page_obj.metadata, dict)
            else None
        )
        if not title:
            # Use the last part of the path as fallback
            title = key.split("/")[-1].replace("-", " ").title()

        article: Article = {
            "title": title,
            "path": key,
        }
        articles.append(article)

    # Sort articles by title
    articles.sort(key=lambda x: x["title"])

    # Calculate pagination
    total_count = len(articles)
    paginated_articles = articles[offset : offset + limit]

    # Calculate pagination info
    has_prev = offset > 0
    has_next = offset + limit < total_count

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "articles": paginated_articles,
            "css_path": css_path,
            "offset": offset,
            "limit": limit,
            "total_count": total_count,
            "has_prev": has_prev,
            "has_next": has_next,
        },
    )


@app.get("/")
async def serve_index_root():
    """Serve index, redirects to /web."""
    return RedirectResponse("/web")
