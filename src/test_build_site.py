from build_site import build_site
from settings import Settings


class TestBuildSite:
    def test_build_site_with_test_knowledge_base(self, test_knowledge_base):
        """Test that build_site builds assets only (no HTML pages)."""
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

        # Verify styles were compiled and copied
        assets_dir = result / "assets" / "styles"
        assert assets_dir.exists()

        # Check that at least one CSS file exists
        css_files = list(assets_dir.glob("index.*.css"))
        assert len(css_files) > 0

        # Verify NO HTML files were created (pages are served from memory)
        html_files = list(result.rglob("*.html"))
        assert len(html_files) == 0, "No HTML files should be generated"
