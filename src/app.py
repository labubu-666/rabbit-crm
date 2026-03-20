from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager
import logging

from src.search import get_search_index, rebuild_search_index

logger = logging.getLogger(__name__)


class PaginationResponse(BaseModel):
    results: list
    offset: int
    limit: int
    count: int


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

    # Shutdown: cleanup if needed
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
