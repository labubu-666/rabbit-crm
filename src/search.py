import re
from typing import List, Dict, Set, Optional
from src.schema import Page


def normalize(text: str) -> str:
    """Converts text to lowercase and replaces non-alphanumeric/whitespace with space."""
    # Replace non-alphanumeric with space, then collapse multiple spaces
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    # Collapse multiple spaces into single space and strip
    return re.sub(r"\s+", " ", text).strip()


def trigrams(text: str) -> List[str]:
    """Pads text, normalizes spaces to underscores, and generates 3-char sequences."""
    s = "  " + normalize(text).replace(" ", "_") + "  "
    return [s[i : i + 3] for i in range(len(s) - 2)]


class SearchIndex:
    """In-memory search index using trigram inverted index for fast text search."""

    def __init__(self):
        self.inverted_index: Dict[str, Set[int]] = {}
        self.pages: Dict[int, Page] = {}
        self.doc_id_to_key: Dict[int, str] = {}

    def build_index(self, pages: Dict[str, Page]) -> None:
        """
        Builds the trigram inverted index from a dictionary of pages.

        Args:
            pages: Dictionary mapping page keys (rel_path) to Page objects
        """
        self.inverted_index.clear()
        self.pages.clear()
        self.doc_id_to_key.clear()

        for doc_id, (key, page) in enumerate(pages.items()):
            # Store page and key mapping
            self.pages[doc_id] = page
            self.doc_id_to_key[doc_id] = key

            # Build searchable text from content and metadata
            searchable_parts = [page.content]

            # Add title from metadata if available
            if isinstance(page.metadata, dict) and "title" in page.metadata:
                searchable_parts.append(page.metadata["title"])

            searchable_text = " ".join(searchable_parts)

            # Generate unique trigrams for this document
            doc_trigrams = set(trigrams(searchable_text))

            # Add doc_id to inverted index for each trigram
            for tg in doc_trigrams:
                if tg not in self.inverted_index:
                    self.inverted_index[tg] = set()
                self.inverted_index[tg].add(doc_id)

    def search(self, query: str, limit: int = 10, offset: int = 0) -> Dict:
        """
        Search for pages matching the query using trigram matching.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)

        Returns:
            Dictionary with results, offset, limit, and count
        """
        if not query or not query.strip():
            return {"results": [], "offset": offset, "limit": limit, "count": 0}

        # Get matching document IDs
        matched_doc_ids = self._filter_docs(query)

        # Paginate results
        total_count = len(matched_doc_ids)
        paginated_ids = matched_doc_ids[offset : offset + limit]

        # Build result objects
        results = []
        for doc_id in paginated_ids:
            page = self.pages[doc_id]
            key = self.doc_id_to_key[doc_id]

            # Extract title
            title = None
            if isinstance(page.metadata, dict):
                title = page.metadata.get("title")
            if not title:
                title = key.split("/")[-1]

            # Create snippet from content (first 200 chars)
            snippet = page.content[:200].strip()
            if len(page.content) > 200:
                snippet += "..."

            results.append(
                {
                    "rel_path": key,
                    "title": title,
                    "snippet": snippet,
                    "url": f"/web/{key}",
                }
            )

        return {
            "results": results,
            "offset": offset,
            "limit": limit,
            "count": total_count,
        }

    def _filter_docs(self, query: str) -> List[int]:
        """
        Filters documents using the trigram inverted index.
        Returns list of doc IDs that contain ALL trigrams from the query.
        """
        query_trigrams = set(trigrams(query))

        if not query_trigrams:
            return []

        # Filter out padding trigrams (those that start/end with spaces)
        # These are position-dependent and shouldn't be used for matching
        non_padding_trigrams = {
            tg
            for tg in query_trigrams
            if not tg.startswith(" ") and not tg.endswith(" ")
        }

        # For very short queries (1-2 chars), use all trigrams including padding
        # Otherwise we'd have no trigrams to match on
        if not non_padding_trigrams:
            query_trigrams_to_use = query_trigrams
        else:
            query_trigrams_to_use = non_padding_trigrams

        if not query_trigrams_to_use:
            return []

        # Initialize with the first trigram's posting list
        first_trigram = next(iter(query_trigrams_to_use))
        current_matches = self.inverted_index.get(first_trigram, set()).copy()

        if not current_matches:
            return []

        # Intersect with remaining trigrams
        for tg in query_trigrams_to_use:
            if tg == first_trigram:
                continue

            tg_matches = self.inverted_index.get(tg, set())
            current_matches.intersection_update(tg_matches)

            # Early exit if no matches remain
            if not current_matches:
                break

        return sorted(list(current_matches))

    def get_index_stats(self) -> Dict:
        """Returns statistics about the search index."""
        return {
            "total_pages": len(self.pages),
            "total_trigrams": len(self.inverted_index),
            "avg_trigrams_per_page": (
                sum(len(tg_set) for tg_set in self.inverted_index.values())
                / len(self.inverted_index)
                if self.inverted_index
                else 0
            ),
        }


# Global search index instance
_search_index: Optional[SearchIndex] = None


def get_search_index() -> SearchIndex:
    """Get the global search index instance."""
    global _search_index
    if _search_index is None:
        _search_index = SearchIndex()
    return _search_index


def rebuild_search_index(pages: Dict[str, Page]) -> None:
    """Rebuild the global search index with the given pages."""
    index = get_search_index()
    index.build_index(pages)
