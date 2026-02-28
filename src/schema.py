from pydantic import BaseModel, Field


class Frontmatter(BaseModel):
    title: str


class Page(BaseModel):
    metadata: dict = Field(default_factory=dict)
    content: str = ""
    html: str = ""
    # helpful fields for consumers
    source_path: str = ""
    rel_path: str = ""
