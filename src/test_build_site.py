from build_site import build_site
from settings import Settings


class TestBuildSite:
    def test_build_site_with_test_knowledge_base(self, test_knowledge_base):
        """Test that build_site works with the test_knowledge_base fixture."""
        pages_dir = test_knowledge_base
        working_dir = pages_dir.parent
        dist_dir = working_dir / "dist"
        styles_dir = working_dir / "styles"

        settings = Settings()

        # Build the site
        result = build_site(
            working_dir=working_dir,
            pages_dir=pages_dir,
            dist_dir=dist_dir,
            styles_dir=styles_dir,
            settings=settings,
        )

        # Verify the dist directory was created
        assert result.exists()
        assert result.is_dir()

        # Verify index.html was created
        index_html = result / "index.html"
        assert index_html.exists()

        # Verify pages were built
        hello_world_html = result / "en" / "hello-world.html"
        assert hello_world_html.exists()

        test_html = result / "en" / "test.html"
        assert test_html.exists()

        # Verify content in hello-world.html
        hello_content = hello_world_html.read_text()
        assert "Hello World" in hello_content
        assert "This is a test page with frontmatter" in hello_content

        # Verify content in test.html
        test_content = test_html.read_text()
        assert "Test Page" in test_content
        assert "This is a test page without frontmatter" in test_content

        # Verify styles were compiled and copied
        assets_dir = result / "assets" / "styles"
        assert assets_dir.exists()

        # Check that at least one CSS file exists
        css_files = list(assets_dir.glob("index.*.css"))
        assert len(css_files) > 0
