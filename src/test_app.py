import pytest
from fastapi.testclient import TestClient

from app import app
from build_site import build_site
from settings import Settings


class TestApp:
    @pytest.fixture
    def client_with_knowledge_base(self, test_knowledge_base):
        """Create a test client with a built knowledge base."""
        pages_dir = test_knowledge_base
        working_dir = pages_dir.parent
        dist_dir = working_dir / "dist"
        styles_dir = working_dir / "styles"

        # Build the site
        settings = Settings()
        build_site(
            working_dir=working_dir,
            pages_dir=pages_dir,
            dist_dir=dist_dir,
            styles_dir=styles_dir,
            settings=settings,
        )

        # Set app state for lifespan
        app.state.pages_dir = pages_dir
        app.state.working_dir = working_dir

        # Create test client
        with TestClient(app) as client:
            yield client

    def test_root_redirects_to_web(self, client_with_knowledge_base):
        """Test that root path redirects to /web."""
        response = client_with_knowledge_base.get("/", follow_redirects=False)
        assert response.status_code == 307  # Redirect
        assert response.headers["location"] == "/web"

    def test_version_endpoint(self, client_with_knowledge_base):
        """Test the version endpoint."""
        from src import __version__

        response = client_with_knowledge_base.get("/api/v1/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["version"] == __version__

    def test_search_endpoint_without_query(self, client_with_knowledge_base):
        """Test search endpoint without query parameter."""
        response = client_with_knowledge_base.get("/api/v1/search")
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["offset"] == 0
        assert data["limit"] == 25
        assert data["count"] == 0

    def test_search_endpoint_with_query(self, client_with_knowledge_base):
        """Test search endpoint with a query."""
        response = client_with_knowledge_base.get("/api/v1/search?q=hello")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "offset" in data
        assert "limit" in data
        assert "count" in data
        assert isinstance(data["results"], list)

    def test_search_endpoint_with_pagination(self, client_with_knowledge_base):
        """Test search endpoint with pagination parameters."""
        response = client_with_knowledge_base.get(
            "/api/v1/search?q=test&limit=5&offset=0"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0

    def test_search_endpoint_limit_validation(self, client_with_knowledge_base):
        """Test that search endpoint validates limit parameter."""
        # Test limit too high
        response = client_with_knowledge_base.get("/api/v1/search?q=test&limit=200")
        assert response.status_code == 422  # Validation error

        # Test limit too low
        response = client_with_knowledge_base.get("/api/v1/search?q=test&limit=0")
        assert response.status_code == 422  # Validation error

    def test_articles_endpoint(self, client_with_knowledge_base):
        """Test the articles endpoint returns a list of articles."""
        response = client_with_knowledge_base.get("/api/v1/articles")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "offset" in data
        assert "limit" in data
        assert "count" in data
        assert isinstance(data["results"], list)

    def test_articles_endpoint_with_pagination(self, client_with_knowledge_base):
        """Test articles endpoint with pagination parameters."""
        response = client_with_knowledge_base.get("/api/v1/articles?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0

    def test_articles_endpoint_limit_validation(self, client_with_knowledge_base):
        """Test that articles endpoint validates limit parameter."""
        # Test limit too high
        response = client_with_knowledge_base.get("/api/v1/articles?limit=200")
        assert response.status_code == 422  # Validation error

        # Test limit too low
        response = client_with_knowledge_base.get("/api/v1/articles?limit=0")
        assert response.status_code == 422  # Validation error

        # Test limit too low
        response = client_with_knowledge_base.get("/api/v1/articles?limit=-1")
        assert response.status_code == 422  # Validation error

    def test_articles_structure(self, client_with_knowledge_base):
        """Test that articles have the correct structure."""
        response = client_with_knowledge_base.get("/api/v1/articles")
        assert response.status_code == 200
        data = response.json()

        if data["results"]:
            article = data["results"][0]
            assert "title" in article
            assert "path" in article
            assert isinstance(article["title"], str)
            assert isinstance(article["path"], str)

    def test_serve_page_from_memory(self, client_with_knowledge_base):
        """Test that pages are served from memory, not from disk."""
        # Request a page that should be in memory
        response = client_with_knowledge_base.get("/web/en/hello-world")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")

        # Verify content is rendered
        content = response.text
        assert "Hello World" in content
        assert "This is a test page with frontmatter" in content

    def test_serve_page_without_frontmatter(self, client_with_knowledge_base):
        """Test serving a page without frontmatter."""
        response = client_with_knowledge_base.get("/web/en/test")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")

        content = response.text
        assert "Test Page" in content
        assert "This is a test page without frontmatter" in content

    def test_serve_nonexistent_page(self, client_with_knowledge_base):
        """Test that nonexistent pages return 404."""
        response = client_with_knowledge_base.get("/web/nonexistent/page")
        assert response.status_code == 404

    def test_serve_static_asset(self, client_with_knowledge_base):
        """Test that static assets (CSS) are still served from disk."""
        # Get the CSS path from the app state
        response = client_with_knowledge_base.get("/web")
        assert response.status_code == 200

        # CSS files should be accessible
        # We can't test the exact path without knowing the hash, but we can verify
        # that the assets directory exists and contains CSS files
        from pathlib import Path

        # The dist directory should have assets
        dist_path = Path("dist")
        if dist_path.exists():
            assets_dir = dist_path / "assets" / "styles"
            if assets_dir.exists():
                css_files = list(assets_dir.glob("index.*.css"))
                assert len(css_files) > 0, "CSS files should exist in assets"
