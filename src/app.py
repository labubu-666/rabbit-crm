from fastapi import FastAPI, Query, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager
import logging

from starlette.responses import Response, FileResponse, RedirectResponse, HTMLResponse

from src.search import get_search_index, rebuild_search_index
from src.schema import Article, Page
from src.pages import compile_and_copy_styles
from src import __version__
from src.admin import router as admin_router

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

app.include_router(admin_router)


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
async def serve_web(request: Request, path: str):
    """Serve pages from memory or static assets from disk."""
    if not path:
        path = "index"

    # First, check if it's a static asset (CSS, JS, images, etc.)
    file_path = dist_path / path
    if file_path.is_file():
        return FileResponse(file_path)

    # Try to serve page from memory
    pages = getattr(app.state, "pages", {})
    templates = getattr(app.state, "templates", None)
    css_path = getattr(app.state, "css_path", None)

    # Try exact path match
    if path in pages:
        page = pages[path]
        return _render_page_from_memory(request, page, path, templates, css_path, pages)

    # Try with /index suffix for directory-style paths
    index_path = f"{path}/index"
    if index_path in pages:
        page = pages[index_path]
        return _render_page_from_memory(
            request, page, index_path, templates, css_path, pages
        )

    # Check if path is a directory and has index
    if path.endswith("/"):
        path_without_slash = path.rstrip("/")
        if path_without_slash in pages:
            page = pages[path_without_slash]
            return _render_page_from_memory(
                request, page, path_without_slash, templates, css_path, pages
            )

    return Response(content="Not Found", status_code=404)


def _render_page_from_memory(
    request: Request, page: Page, key: str, templates, css_path: str, pages: dict
) -> HTMLResponse:
    """Render a page from memory using templates."""
    if not templates:
        return Response(content="Templates not configured", status_code=500)

    # Get title from metadata or use fallback
    title = page.metadata.get("title") if isinstance(page.metadata, dict) else None
    if not title:
        title = key.split("/")[-1].replace("-", " ").title()

    # Determine if this is an index page
    is_index_page = key.endswith("/index") or key == "index"

    if is_index_page:
        # Prepare articles list for index pages
        articles = []
        for page_key, page_obj in pages.items():
            # Skip index pages
            if page_key.endswith("/index") or page_key == "index":
                continue

            # Get title from metadata or use fallback
            page_title = (
                page_obj.metadata.get("title")
                if isinstance(page_obj.metadata, dict)
                else None
            )
            if not page_title:
                page_title = page_key.split("/")[-1].replace("-", " ").title()

            article: Article = {
                "title": page_title,
                "path": page_key,
            }
            articles.append(article)

        # Sort articles by title
        articles.sort(key=lambda x: x["title"])

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "title": title,
                "css_path": css_path,
                "articles": articles,
                "version": __version__,
            },
        )
    else:
        # Render article page
        return templates.TemplateResponse(
            request=request,
            name="article.html",
            context={
                "title": title,
                "content": page.html,
                "css_path": css_path,
                "version": __version__,
            },
        )


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
            "version": __version__,
        },
    )


@app.get("/")
async def serve_index_root():
    """Serve index, redirects to /web."""
    return RedirectResponse("/web")
