from pydantic import BaseModel, Field
from typing import TypedDict


class Frontmatter(BaseModel):
    title: str


class Page(BaseModel):
    metadata: dict = Field(default_factory=dict)
    content: str = ""
    html: str = ""
    # helpful fields for consumers
    source_path: str = ""
    rel_path: str = ""


class Article(TypedDict):
    """Article metadata for listing in index pages."""

    title: str
    path: str
