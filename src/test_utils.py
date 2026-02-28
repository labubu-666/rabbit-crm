from pathlib import Path
import pytest

from src.utils import create_folder, load_pages


class TestCreateFolder:
    def test_create_folder_creates_directory(self, tmp_path):
        d = tmp_path / "dist"
        assert not d.exists()

        result = create_folder(d)
        assert isinstance(result, Path)
        assert result.exists() and result.is_dir()

        # idempotent call
        result2 = create_folder(d)
        assert result2 == result

    def test_create_folder_raises_when_file_exists(self, tmp_path):
        f = tmp_path / "dist"
        f.write_text("I am a file")
        assert f.exists() and f.is_file()

        with pytest.raises(RuntimeError):
            create_folder(f)

def test_load_single_page_without_frontmatter(tmp_path):
    pages = tmp_path / "pages"
    pages.mkdir()
    f = pages / "foo.md"
    f.write_text("# Hello\n\nThis is a test page.")

    result = load_pages(pages)
    assert isinstance(result, dict)
    assert "foo" in result

    page = result["foo"]
    assert page.metadata == {}
    assert "This is a test page." in page.content
    # html should contain the heading text in some form
    assert "Hello" in page.html


def test_load_page_with_frontmatter(tmp_path):
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    f = pages / "de" / "index.md"
    f.parent.mkdir(parents=True)
    f.write_text("""---
title: Hello
tags:
  - a
  - b
---
# Title\n\nBody text
""")

    result = load_pages(pages)
    assert "de/index" in result
    page = result["de/index"]
    assert isinstance(page.metadata, dict)
    # title should be present either as parsed YAML or fallback
    assert page.metadata.get("title") == "Hello"
    assert "Body text" in page.content
    assert "Title" in page.html


def test_missing_pages_dir_returns_empty(tmp_path):
    no_dir = tmp_path / "no-pages"
    assert not no_dir.exists()

    result = load_pages(no_dir)
    assert result == {}
