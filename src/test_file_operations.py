"""Tests for file operations."""

from src.file_operations import (
    validate_article_path,
    write_article,
    read_article,
    delete_article,
)


def test_validate_article_path():
    """Test path validation."""
    # Valid paths
    assert validate_article_path("article")
    assert validate_article_path("en/article")
    assert validate_article_path("en/sub/article")

    # Invalid paths
    assert not validate_article_path("")
    assert not validate_article_path("../article")
    assert not validate_article_path("/article")
    assert not validate_article_path("article/../other")
    assert not validate_article_path("article<test>")


def test_write_and_read_article(tmp_path):
    """Test writing and reading articles."""
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()

    # Write article
    result = write_article(pages_dir, "test-article", "Test Title", "Test content")
    assert result is not None
    assert result.exists()

    # Read article
    title, content = read_article(pages_dir, "test-article")
    assert title == "Test Title"
    assert content.strip() == "Test content"


def test_write_article_with_subdirectory(tmp_path):
    """Test writing article in subdirectory."""
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()

    # Write article in subdirectory
    result = write_article(pages_dir, "en/test-article", "Test Title", "Test content")
    assert result is not None
    assert result.exists()
    assert (pages_dir / "en" / "test-article.md").exists()


def test_delete_article(tmp_path):
    """Test deleting articles."""
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()

    # Write article
    write_article(pages_dir, "test-article", "Test Title", "Test content")

    # Delete article
    assert delete_article(pages_dir, "test-article")
    assert not (pages_dir / "test-article.md").exists()

    # Try to delete non-existent article
    assert not delete_article(pages_dir, "non-existent")


def test_invalid_path_operations(tmp_path):
    """Test operations with invalid paths."""
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()

    # Write with invalid path
    result = write_article(pages_dir, "../test", "Title", "Content")
    assert result is None

    # Read with invalid path
    result = read_article(pages_dir, "../test")
    assert result is None

    # Delete with invalid path
    assert not delete_article(pages_dir, "../test")
