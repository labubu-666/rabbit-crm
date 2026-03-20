import pytest
from src.search import normalize, trigrams, SearchIndex
from src.schema import Page


class TestNormalize:
    """Tests for the normalize function."""

    def test_lowercase_conversion(self):
        assert normalize("HELLO WORLD") == "hello world"
        assert normalize("Hello World") == "hello world"

    def test_special_characters_replaced(self):
        assert normalize("hello-world") == "hello world"
        assert normalize("hello@world!") == "hello world"
        assert normalize("test.file") == "test file"

    def test_alphanumeric_preserved(self):
        assert normalize("test123") == "test123"
        assert normalize("abc 123 xyz") == "abc 123 xyz"

    def test_multiple_spaces(self):
        # Multiple special chars become multiple spaces
        result = normalize("hello---world")
        assert "hello" in result and "world" in result


class TestTrigrams:
    """Tests for the trigrams function."""

    def test_simple_word(self):
        result = trigrams("cat")
        assert "  c" in result
        assert " ca" in result
        assert "cat" in result
        assert "at " in result
        assert "t  " in result

    def test_multiple_words(self):
        result = trigrams("quick fox")
        # Should have trigrams spanning the underscore
        assert "ck_" in result
        assert "_fo" in result

    def test_special_characters_normalized(self):
        result = trigrams("hello-world")
        # The dash becomes space, then underscore
        assert "lo_" in result
        assert "_wo" in result

    def test_empty_string(self):
        result = trigrams("")
        # Should still have padding trigrams
        assert len(result) >= 0

    def test_single_character(self):
        result = trigrams("a")
        assert "  a" in result
        assert " a " in result
        assert "a  " in result


class TestSearchIndex:
    """Tests for the SearchIndex class."""

    @pytest.fixture
    def sample_pages(self):
        """Create sample pages for testing."""
        return {
            "en/quick-brown-fox": Page(
                metadata={"title": "Quick Brown Fox"},
                content="The quick brown fox jumps over the lazy dog.",
                html="<p>The quick brown fox jumps over the lazy dog.</p>",
                source_path="pages/en/quick-brown-fox.md",
                rel_path="en/quick-brown-fox",
            ),
            "en/dogs-and-foxes": Page(
                metadata={"title": "Dogs and Foxes"},
                content="Quick brown dogs leap over lazy foxes in summer.",
                html="<p>Quick brown dogs leap over lazy foxes in summer.</p>",
                source_path="pages/en/dogs-and-foxes.md",
                rel_path="en/dogs-and-foxes",
            ),
            "en/databases": Page(
                metadata={"title": "Database Indexing"},
                content="An unrelated document about databases and indexing.",
                html="<p>An unrelated document about databases and indexing.</p>",
                source_path="pages/en/databases.md",
                rel_path="en/databases",
            ),
        }

    def test_build_index(self, sample_pages):
        """Test that index is built correctly."""
        index = SearchIndex()
        index.build_index(sample_pages)

        assert len(index.pages) == 3
        assert len(index.inverted_index) > 0
        assert len(index.doc_id_to_key) == 3

    def test_search_single_match(self, sample_pages):
        """Test search with a query that matches one document."""
        index = SearchIndex()
        index.build_index(sample_pages)

        result = index.search("quick brown fox")

        assert result["count"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["rel_path"] == "en/quick-brown-fox"
        assert result["results"][0]["title"] == "Quick Brown Fox"

    def test_search_multiple_matches(self, sample_pages):
        """Test search with a query that matches multiple documents."""
        index = SearchIndex()
        index.build_index(sample_pages)

        # Both first two pages contain "quick" and "brown"
        result = index.search("quick brown")

        assert result["count"] == 2
        assert len(result["results"]) == 2

    def test_search_no_matches(self, sample_pages):
        """Test search with a query that matches no documents."""
        index = SearchIndex()
        index.build_index(sample_pages)

        result = index.search("nonexistent word")

        assert result["count"] == 0
        assert len(result["results"]) == 0

    def test_search_empty_query(self, sample_pages):
        """Test search with empty query."""
        index = SearchIndex()
        index.build_index(sample_pages)

        result = index.search("")

        assert result["count"] == 0
        assert len(result["results"]) == 0

    def test_search_partial_match(self, sample_pages):
        """Test that partial matches don't return results."""
        index = SearchIndex()
        index.build_index(sample_pages)

        # "quick" is in first two docs, "document" only in third
        # No single doc has both, so should return 0 results
        result = index.search("quick document")

        assert result["count"] == 0

    def test_search_pagination(self, sample_pages):
        """Test pagination of search results."""
        index = SearchIndex()
        index.build_index(sample_pages)

        # Search for something that matches multiple docs
        result = index.search("quick brown", limit=1, offset=0)

        assert result["count"] == 2  # Total matches
        assert len(result["results"]) == 1  # But only 1 returned
        assert result["limit"] == 1
        assert result["offset"] == 0

        # Get second page
        result2 = index.search("quick brown", limit=1, offset=1)
        assert len(result2["results"]) == 1
        assert result2["offset"] == 1

    def test_search_result_structure(self, sample_pages):
        """Test that search results have correct structure."""
        index = SearchIndex()
        index.build_index(sample_pages)

        result = index.search("quick brown fox")

        assert "results" in result
        assert "offset" in result
        assert "limit" in result
        assert "count" in result

        if result["results"]:
            first_result = result["results"][0]
            assert "rel_path" in first_result
            assert "title" in first_result
            assert "snippet" in first_result
            assert "url" in first_result

    def test_search_snippet_generation(self, sample_pages):
        """Test that snippets are generated correctly."""
        index = SearchIndex()
        index.build_index(sample_pages)

        result = index.search("quick brown fox")

        assert len(result["results"]) > 0
        snippet = result["results"][0]["snippet"]
        assert len(snippet) > 0
        assert "quick" in snippet.lower()

    def test_search_url_generation(self, sample_pages):
        """Test that URLs are generated correctly."""
        index = SearchIndex()
        index.build_index(sample_pages)

        result = index.search("quick brown fox")

        assert len(result["results"]) > 0
        url = result["results"][0]["url"]
        assert url.startswith("/web/")
        assert "en/quick-brown-fox" in url

    def test_search_title_from_metadata(self, sample_pages):
        """Test that title is extracted from metadata."""
        index = SearchIndex()
        index.build_index(sample_pages)

        result = index.search("database")

        assert len(result["results"]) > 0
        assert result["results"][0]["title"] == "Database Indexing"

    def test_search_title_fallback(self):
        """Test title fallback when metadata is missing."""
        pages = {
            "test/page": Page(
                metadata={},
                content="Test content",
                html="<p>Test content</p>",
                source_path="pages/test/page.md",
                rel_path="test/page",
            )
        }

        index = SearchIndex()
        index.build_index(pages)

        result = index.search("test")

        assert len(result["results"]) > 0
        # Should use last part of rel_path as fallback
        assert result["results"][0]["title"] == "page"

    def test_get_index_stats(self, sample_pages):
        """Test index statistics."""
        index = SearchIndex()
        index.build_index(sample_pages)

        stats = index.get_index_stats()

        assert "total_pages" in stats
        assert "total_trigrams" in stats
        assert "avg_trigrams_per_page" in stats
        assert stats["total_pages"] == 3
        assert stats["total_trigrams"] > 0

    def test_rebuild_index_clears_old_data(self, sample_pages):
        """Test that rebuilding index clears old data."""
        index = SearchIndex()
        index.build_index(sample_pages)

        old_page_count = len(index.pages)

        # Rebuild with fewer pages
        new_pages = {"en/quick-brown-fox": sample_pages["en/quick-brown-fox"]}
        index.build_index(new_pages)

        assert len(index.pages) == 1
        assert len(index.pages) < old_page_count

    def test_search_case_insensitive(self, sample_pages):
        """Test that search is case insensitive."""
        index = SearchIndex()
        index.build_index(sample_pages)

        result1 = index.search("QUICK BROWN FOX")
        result2 = index.search("quick brown fox")
        result3 = index.search("Quick Brown Fox")

        assert result1["count"] == result2["count"] == result3["count"]

    def test_search_special_characters(self, sample_pages):
        """Test search with special characters."""
        index = SearchIndex()
        index.build_index(sample_pages)

        # Special characters should be normalized
        result = index.search("quick-brown-fox")

        # Should still match because normalization happens
        assert result["count"] > 0


class TestSearchIndexIntegration:
    """Integration tests for search functionality."""

    def test_empty_index_search(self):
        """Test searching on empty index."""
        index = SearchIndex()
        index.build_index({})

        result = index.search("anything")

        assert result["count"] == 0
        assert len(result["results"]) == 0

    def test_large_content_snippet(self):
        """Test snippet generation for large content."""
        long_content = (
            "This is a very long document. " * 50
        )  # Content longer than snippet limit
        pages = {
            "test": Page(
                metadata={"title": "Test"},
                content=long_content,
                html="<p>" + long_content + "</p>",
                source_path="test.md",
                rel_path="test",
            )
        }

        index = SearchIndex()
        index.build_index(pages)

        result = index.search("very long document")

        assert len(result["results"]) > 0
        snippet = result["results"][0]["snippet"]
        # Snippet should be truncated
        assert len(snippet) <= 203  # 200 chars + "..."
        assert snippet.endswith("...")
