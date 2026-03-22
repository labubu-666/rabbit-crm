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

    def test_version_endpoint(self, client_with_knowledge_base):
        """Test the version endpoint."""
        response = client_with_knowledge_base.get("/api/v1/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.0.0"

    def test_search_endpoint_without_query(self, client_with_knowledge_base):
        """Test search endpoint without query parameter."""
        response = client_with_knowledge_base.get("/api/v1/search")
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["offset"] == 0
        assert data["limit"] == 10
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

    def test_root_redirects_to_web(self, client_with_knowledge_base):
        """Test that root path redirects to /web."""
        response = client_with_knowledge_base.get("/", follow_redirects=False)
        assert response.status_code == 307  # Redirect
        assert response.headers["location"] == "/web"
