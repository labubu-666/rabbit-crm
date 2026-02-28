from pathlib import Path
import pytest

from src.utils import create_folder, load_pages, parse_frontmatter


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

class TestLoadPages:
    def test_load_single_page_without_frontmatter(self, tmp_path):
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


    def test_load_page_with_frontmatter(self, tmp_path):
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


    def test_missing_pages_dir_returns_empty(self, tmp_path):
        no_dir = tmp_path / "no-pages"
        assert not no_dir.exists()

        result = load_pages(no_dir)
        assert result == {}

class TestParseFrontmatter:
    def test_parse_frontmatter(self):
        """Test parsing valid frontmatter with YAML content."""
        text = """---
title: Hello World
tags:
  - python
  - testing
author: John Doe
---
# Content starts here

This is the body of the document.
"""
        metadata, content = parse_frontmatter(text)
        
        assert isinstance(metadata, dict)
        assert metadata["title"] == "Hello World"
        assert metadata["tags"] == ["python", "testing"]
        assert metadata["author"] == "John Doe"
        assert content.strip().startswith("# Content starts here")
        assert "This is the body of the document." in content

    @pytest.mark.parametrize("text,expected_metadata,expected_content_start", [
        # No frontmatter at all
        (
            "# Just a heading\n\nSome content",
            {},
            "# Just a heading"
        ),
        # Missing closing delimiter
        (
            "---\ntitle: Test\n# No closing delimiter\nContent here",
            {},
            "---\ntitle: Test"
        ),
    ])
    def test_parse_frontmatter_valid_inputs(self, text, expected_metadata, expected_content_start):
        """Test various edge cases with valid inputs."""
        metadata, content = parse_frontmatter(text)
        
        assert isinstance(metadata, dict)
        assert metadata == expected_metadata
        assert content.strip().startswith(expected_content_start.strip())

    def test_parse_frontmatter_empty_frontmatter(self):
        """Test that empty frontmatter (no title) raises an exception."""
        text = "---\n---\nContent only"
        
        with pytest.raises(Exception):  # Pydantic ValidationError
            parse_frontmatter(text)

    def test_parse_frontmatter_invalid_yaml(self):
        """Test that invalid YAML raises an exception."""
        text = "---\n{invalid: yaml: content:\n---\nContent after"
        
        with pytest.raises(Exception):  # yaml.YAMLError or similar
            parse_frontmatter(text)

    def test_parse_frontmatter_non_dict_yaml(self):
        """Test that non-dict YAML (e.g., a list) raises an exception."""
        text = "---\n- item1\n- item2\n---\nContent"
        
        with pytest.raises(ValueError, match="Frontmatter must be a YAML dict"):
            parse_frontmatter(text)

    def test_parse_frontmatter_missing_title(self):
        """Test that frontmatter without required title field raises an exception."""
        text = "---\nauthor: John Doe\n---\nContent"
        
        with pytest.raises(Exception):  # Pydantic ValidationError
            parse_frontmatter(text)
