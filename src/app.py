from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional

from src.search import get_search_index


class PaginationResponse(BaseModel):
    results: list
    offset: int
    limit: int
    count: int


app = FastAPI(docs_url="/api/docs", title="rabbit", version="0.0.0")


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
