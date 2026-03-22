from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager
import logging

from starlette.responses import Response, FileResponse, RedirectResponse

from src.search import get_search_index, rebuild_search_index

logger = logging.getLogger(__name__)


class PaginationResponse(BaseModel):
    results: list
    offset: int
    limit: int
    count: int


dist_path = Path("dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup and shutdown."""
    # Startup: Load pages and build search index
    if hasattr(app.state, "pages_dir") and hasattr(app.state, "working_dir"):
        from src.pages import load_pages

        pages_dir = Path(app.state.pages_dir)
        working_dir = Path(app.state.working_dir)

        logger.info("Loading pages for search index...")
        pages = load_pages(pages_dir, working_dir)
        logger.info(f"Loaded {len(pages)} page(s)")

        logger.info("Building search index...")
        rebuild_search_index(pages)
        logger.info("Search index built successfully")

    yield

    logger.info("Shutting down app...")


app = FastAPI(docs_url="/api/docs", title="rabbit", version="0.0.0", lifespan=lifespan)


@app.get("/api/v1/version")
async def version():
    return {"version": "0.0.0"}


@app.get("/api/v1/search", response_model=PaginationResponse)
async def search(
    q: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
    """Search through indexed pages using trigram matching."""
    if not q:
        return PaginationResponse(results=[], offset=offset, limit=limit, count=0)

    search_index = get_search_index()
    result = search_index.search(q, limit=limit, offset=offset)

    return PaginationResponse(**result)


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


@app.get("/web")
async def serve_web_root():
    """Serve web/index."""
    index_path = dist_path / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)
    return Response(content="Not Found", status_code=404)


@app.get("/")
async def serve_index_root():
    """Serve index, redirects to /web."""
    return RedirectResponse("/web")
