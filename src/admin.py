"""Admin panel with basic authentication and CRUD operations for articles."""

import logging
import secrets
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from settings import Settings
from src.file_operations import (
    write_article,
    read_article,
    delete_article,
    validate_article_path,
)

logger = logging.getLogger(__name__)

settings = Settings()
settings.model_validate(settings)

security = HTTPBasic()

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_credentials(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    """Verify basic authentication credentials."""
    is_correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"), settings.admin_username.encode("utf8")
    )
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"), settings.admin_password.encode("utf8")
    )

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# Pydantic models for API
class ArticleCreate(BaseModel):
    title: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    content: str = Field(default="")


class ArticleUpdate(BaseModel):
    title: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    content: str = Field(default="")


class ArticleResponse(BaseModel):
    title: str
    path: str
    content: str


# API Endpoints
@router.get("/api/v1/articles")
async def admin_list_articles(
    request: Request,
    username: Annotated[str, Depends(verify_credentials)],
):
    """List all articles (API endpoint)."""
    pages = getattr(request.app.state, "pages", {})

    articles = []
    for key, page in pages.items():
        # Skip index pages
        if key.endswith("/index") or key == "index":
            continue

        title = page.metadata.get("title") if isinstance(page.metadata, dict) else None
        if not title:
            title = key.split("/")[-1].replace("-", " ").title()

        articles.append(
            {
                "title": title,
                "path": key,
                "content": page.content,
            }
        )

    articles.sort(key=lambda x: x["title"])
    return {"articles": articles}


@router.get("/api/v1/articles/{path:path}")
async def admin_get_article(
    path: str,
    request: Request,
    username: Annotated[str, Depends(verify_credentials)],
):
    """Get a single article (API endpoint)."""
    pages_dir = Path(getattr(request.app.state, "pages_dir", "pages"))

    result = read_article(pages_dir, path)
    if result is None:
        raise HTTPException(status_code=404, detail="Article not found")

    title, content = result
    return ArticleResponse(title=title, path=path, content=content)


@router.post("/api/v1/articles", status_code=status.HTTP_201_CREATED)
async def admin_create_article(
    article: ArticleCreate,
    request: Request,
    username: Annotated[str, Depends(verify_credentials)],
):
    """Create a new article (API endpoint)."""
    pages_dir = Path(getattr(request.app.state, "pages_dir", "pages"))

    if not validate_article_path(article.path):
        raise HTTPException(status_code=400, detail="Invalid article path")

    # Check if article already exists
    file_path = pages_dir / f"{article.path}.md"
    if file_path.exists():
        raise HTTPException(status_code=409, detail="Article already exists")

    result = write_article(pages_dir, article.path, article.title, article.content)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to create article")

    # Reload pages and rebuild search index
    await reload_app_state(request)

    return ArticleResponse(
        title=article.title, path=article.path, content=article.content
    )


@router.put("/api/v1/articles/{path:path}")
async def admin_update_article(
    path: str,
    article: ArticleUpdate,
    request: Request,
    username: Annotated[str, Depends(verify_credentials)],
):
    """Update an existing article (API endpoint)."""
    pages_dir = Path(getattr(request.app.state, "pages_dir", "pages"))

    if not validate_article_path(path):
        raise HTTPException(status_code=400, detail="Invalid article path")

    # Check if article exists
    file_path = pages_dir / f"{path}.md"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Article not found")

    result = write_article(pages_dir, path, article.title, article.content)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to update article")

    # Reload pages and rebuild search index
    await reload_app_state(request)

    return ArticleResponse(title=article.title, path=path, content=article.content)


@router.delete("/api/v1/articles/{path:path}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_article(
    path: str,
    request: Request,
    username: Annotated[str, Depends(verify_credentials)],
):
    """Delete an article (API endpoint)."""
    pages_dir = Path(getattr(request.app.state, "pages_dir", "pages"))

    if not validate_article_path(path):
        raise HTTPException(status_code=400, detail="Invalid article path")

    success = delete_article(pages_dir, path)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found")

    # Reload pages and rebuild search index
    await reload_app_state(request)

    return None


# Web Interface Endpoints
@router.get("", response_class=HTMLResponse)
async def admin_index(
    request: Request,
    username: Annotated[str, Depends(verify_credentials)],
):
    """Admin panel home page - list all articles."""
    pages = getattr(request.app.state, "pages", {})

    articles = []
    for key, page in pages.items():
        # Skip index pages
        if key.endswith("/index") or key == "index":
            continue

        title = page.metadata.get("title") if isinstance(page.metadata, dict) else None
        if not title:
            title = key.split("/")[-1].replace("-", " ").title()

        articles.append(
            {
                "title": title,
                "path": key,
            }
        )

    articles.sort(key=lambda x: x["title"])

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Panel</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Admin Panel</h1>
        <p>Logged in as: {username}</p>
        <h2>Articles</h2>
        <p><a href="/admin/new">Create New Article</a></p>
        <table border="1">
            <thead>
                <tr>
                    <th>Title</th>
                    <th>Path</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    """

    for article in articles:
        html += f"""
                <tr>
                    <td>{article["title"]}</td>
                    <td>{article["path"]}</td>
                    <td>
                        <a href="/admin/edit/{article["path"]}">Edit</a> |
                        <form method="post" action="/admin/delete/{article["path"]}" style="display:inline;">
                            <button type="submit" onclick="return confirm('Are you sure you want to delete this article?')">Delete</button>
                        </form>
                    </td>
                </tr>
        """

    html += """
            </tbody>
        </table>
    </body>
    </html>
    """

    return HTMLResponse(content=html)


@router.get("/new", response_class=HTMLResponse)
async def admin_new_article_form(
    request: Request,
    username: Annotated[str, Depends(verify_credentials)],
):
    """Show form to create a new article."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Create New Article</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Create New Article</h1>
        <form method="post" action="/admin/create">
            <p>
                <label>Title (required):<br>
                <input type="text" name="title" required style="width: 400px;"></label>
            </p>
            <p>
                <label>Path (required, e.g., "en/my-article" or "my-article"):<br>
                <input type="text" name="path" required style="width: 400px;"></label>
            </p>
            <p>
                <label>Content (markdown):<br>
                <textarea name="content" rows="20" cols="80"></textarea></label>
            </p>
            <p>
                <button type="submit">Create Article</button>
                <a href="/admin">Cancel</a>
            </p>
        </form>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.post("/create")
async def admin_create_article_form(
    request: Request,
    username: Annotated[str, Depends(verify_credentials)],
    title: Annotated[str, Form()],
    path: Annotated[str, Form()],
    content: Annotated[str, Form()] = "",
):
    """Handle form submission to create a new article."""
    pages_dir = Path(getattr(request.app.state, "pages_dir", "pages"))

    if not validate_article_path(path):
        return HTMLResponse(
            content="<h1>Error</h1><p>Invalid article path</p><a href='/admin'>Back</a>",
            status_code=400,
        )

    # Check if article already exists
    file_path = pages_dir / f"{path}.md"
    if file_path.exists():
        return HTMLResponse(
            content="<h1>Error</h1><p>Article already exists</p><a href='/admin'>Back</a>",
            status_code=409,
        )

    result = write_article(pages_dir, path, title, content)
    if result is None:
        return HTMLResponse(
            content="<h1>Error</h1><p>Failed to create article</p><a href='/admin'>Back</a>",
            status_code=500,
        )

    # Reload pages and rebuild search index
    await reload_app_state(request)

    return RedirectResponse(url="/admin", status_code=303)


@router.get("/edit/{path:path}", response_class=HTMLResponse)
async def admin_edit_article_form(
    path: str,
    request: Request,
    username: Annotated[str, Depends(verify_credentials)],
):
    """Show form to edit an existing article."""
    pages_dir = Path(getattr(request.app.state, "pages_dir", "pages"))

    result = read_article(pages_dir, path)
    if result is None:
        return HTMLResponse(
            content="<h1>Error</h1><p>Article not found</p><a href='/admin'>Back</a>",
            status_code=404,
        )

    title, content = result

    # Escape HTML in content
    import html as html_module

    title_escaped = html_module.escape(title)
    content_escaped = html_module.escape(content)

    path_escaped = html_module.escape(path)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Edit Article</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Edit Article</h1>
        <form method="post" action="/admin/update/{path}">
            <input type="hidden" name="old_path" value="{path_escaped}">
            <p>
                <label>Title (required):<br>
                <input type="text" name="title" value="{title_escaped}" required style="width: 400px;"></label>
            </p>
            <p>
                <label>Path (required, e.g., "en/my-article" or "my-article"):<br>
                <input type="text" name="new_path" value="{path_escaped}" required style="width: 400px;"></label>
            </p>
            <p>
                <label>Content (markdown):<br>
                <textarea name="content" rows="20" cols="80">{content_escaped}</textarea></label>
            </p>
            <p>
                <button type="submit">Update Article</button>
                <a href="/admin">Cancel</a>
            </p>
        </form>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.post("/update/{path:path}")
async def admin_update_article_form(
    path: str,
    request: Request,
    username: Annotated[str, Depends(verify_credentials)],
    title: Annotated[str, Form()],
    old_path: Annotated[str, Form()],
    new_path: Annotated[str, Form()],
    content: Annotated[str, Form()] = "",
):
    """Handle form submission to update an article."""
    pages_dir = Path(getattr(request.app.state, "pages_dir", "pages"))

    # Validate old path
    if not validate_article_path(old_path):
        return HTMLResponse(
            content="<h1>Error</h1><p>Invalid old article path</p><a href='/admin'>Back</a>",
            status_code=400,
        )

    # Validate new path
    if not validate_article_path(new_path):
        return HTMLResponse(
            content="<h1>Error</h1><p>Invalid new article path</p><a href='/admin'>Back</a>",
            status_code=400,
        )

    # Check if old article exists
    old_file_path = pages_dir / f"{old_path}.md"
    if not old_file_path.exists():
        return HTMLResponse(
            content="<h1>Error</h1><p>Article not found</p><a href='/admin'>Back</a>",
            status_code=404,
        )

    # If path changed, check if new path already exists
    if old_path != new_path:
        new_file_path = pages_dir / f"{new_path}.md"
        if new_file_path.exists():
            return HTMLResponse(
                content="<h1>Error</h1><p>An article with the new path already exists</p><a href='/admin'>Back</a>",
                status_code=409,
            )

        # Delete old file
        if not delete_article(pages_dir, old_path):
            return HTMLResponse(
                content="<h1>Error</h1><p>Failed to delete old article</p><a href='/admin'>Back</a>",
                status_code=500,
            )

    # Write article with new path
    result = write_article(pages_dir, new_path, title, content)
    if result is None:
        return HTMLResponse(
            content="<h1>Error</h1><p>Failed to update article</p><a href='/admin'>Back</a>",
            status_code=500,
        )

    # Reload pages and rebuild search index
    await reload_app_state(request)

    return RedirectResponse(url="/admin", status_code=303)


@router.post("/delete/{path:path}")
async def admin_delete_article_form(
    path: str,
    request: Request,
    username: Annotated[str, Depends(verify_credentials)],
):
    """Handle form submission to delete an article."""
    pages_dir = Path(getattr(request.app.state, "pages_dir", "pages"))

    if not validate_article_path(path):
        return HTMLResponse(
            content="<h1>Error</h1><p>Invalid article path</p><a href='/admin'>Back</a>",
            status_code=400,
        )

    success = delete_article(pages_dir, path)
    if not success:
        return HTMLResponse(
            content="<h1>Error</h1><p>Article not found</p><a href='/admin'>Back</a>",
            status_code=404,
        )

    # Reload pages and rebuild search index
    await reload_app_state(request)

    return RedirectResponse(url="/admin", status_code=303)


async def reload_app_state(request: Request):
    """Reload pages and rebuild search index after CRUD operations."""
    from src.pages import load_pages, compile_and_copy_styles
    from src.search import rebuild_search_index

    pages_dir = Path(getattr(request.app.state, "pages_dir", "pages"))
    working_dir = Path(getattr(request.app.state, "working_dir", "."))
    dist_dir = Path(getattr(request.app.state, "dist_dir", "dist"))
    styles_dir = Path(getattr(request.app.state, "styles_dir", "styles"))

    logger.info("Reloading pages after CRUD operation...")
    pages = load_pages(pages_dir, working_dir)
    request.app.state.pages = pages
    logger.info(f"Reloaded {len(pages)} page(s)")

    # Recompile styles
    logger.info("Recompiling styles...")
    css_path = compile_and_copy_styles(styles_dir, dist_dir)
    request.app.state.css_path = css_path

    # Rebuild search index
    logger.info("Rebuilding search index...")
    rebuild_search_index(pages)
    logger.info("Search index rebuilt")
