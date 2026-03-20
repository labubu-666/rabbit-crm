import logging

from pages import load_pages


class TestLoadPages:
    def test_load_page_without_frontmatter(self, tmp_path):
        pages = tmp_path / "pages"
        pages.mkdir()
        f = pages / "foo.md"
        f.write_text(
            """# Hello

This is a test page."""
        )

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
        f.write_text(
            """---
title: Hello
tags:
  - a
  - b
---
# Title

Body text
"""
        )

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

    def test_missing_pages_dir_logs_info(self, tmp_path, caplog):
        """Test that missing pages directory logs an info message."""
        no_dir = tmp_path / "no-pages"
        assert not no_dir.exists()

        with caplog.at_level(logging.INFO):
            result = load_pages(no_dir)

        assert result == {}
        assert "does not exist" in caplog.text
        assert str(no_dir.resolve()) in caplog.text

    def test_duplicate_page_key_logs_warning(self, tmp_path, caplog):
        """Test that duplicate page keys log a warning."""
        pages = tmp_path / "pages"
        pages.mkdir()

        # Create two files that will have the same key (foo)
        f1 = pages / "foo.md"
        f1.write_text(
            """# First

First content"""
        )

        f2 = pages / "foo.markdown"
        f2.write_text(
            """# Second

Second content"""
        )

        with caplog.at_level(logging.WARNING):
            result = load_pages(pages)

        assert "foo" in result
        # One of them should override the other
        assert "Duplicate page key" in caplog.text
        assert "foo" in caplog.text
        assert "will override previous" in caplog.text

    def test_skips_hidden_files(self, tmp_path):
        """Test that hidden files and directories are skipped."""
        pages = tmp_path / "pages"
        pages.mkdir()

        # Create a hidden file
        hidden = pages / ".hidden.md"
        hidden.write_text(
            """# Hidden

This should be skipped"""
        )

        # Create a file in a hidden directory
        hidden_dir = pages / ".hidden_dir"
        hidden_dir.mkdir()
        hidden_file = hidden_dir / "file.md"
        hidden_file.write_text(
            """# Also Hidden

This should also be skipped"""
        )

        # Create a normal file
        normal = pages / "normal.md"
        normal.write_text(
            """# Normal

This should be loaded"""
        )

        result = load_pages(pages)

        assert "normal" in result
        assert ".hidden" not in result
        assert ".hidden_dir/file" not in result
        assert len(result) == 1

    def test_load_html_file_without_markdown_rendering(self, tmp_path):
        """Test that HTML files are loaded as-is without markdown rendering."""
        pages = tmp_path / "pages"
        pages.mkdir()

        html_file = pages / "raw.html"
        html_file.write_text(
            """<div class="custom">
<h1>Raw HTML</h1>
<p>This is <strong>raw</strong> HTML.</p>
</div>"""
        )

        result = load_pages(pages)

        assert "raw" in result
        page = result["raw"]
        assert page.metadata == {}
        assert '<div class="custom">' in page.html
        assert "<strong>raw</strong>" in page.html
        # Content and HTML should be the same for HTML files
        assert page.content == page.html
