import pytest

from frontmatter import parse_frontmatter


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

    @pytest.mark.parametrize(
        "text,expected_metadata,expected_content_start",
        [
            # No frontmatter at all
            ("# Just a heading\n\nSome content", {}, "# Just a heading"),
            # Missing closing delimiter
            (
                "---\ntitle: Test\n# No closing delimiter\nContent here",
                {},
                "---\ntitle: Test",
            ),
        ],
    )
    def test_parse_frontmatter_valid_inputs(
        self, text, expected_metadata, expected_content_start
    ):
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
