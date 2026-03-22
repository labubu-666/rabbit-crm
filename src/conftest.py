import pytest


@pytest.fixture
def test_knowledge_base(tmp_path):
    """Create a test knowledge base structure with pages, templates, and styles.

    Yields the pages_dir path that can be used to test build_site.

    The structure created:
    - pages/
      - en/
        - hello-world.md (with frontmatter)
        - test.md (without frontmatter)
    - templates/
      - article.html
      - index.html
    - styles/
      - index.scss
    """
    # Create pages directory with test content
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()

    en_dir = pages_dir / "en"
    en_dir.mkdir()

    # Create a page with frontmatter
    hello_world = en_dir / "hello-world.md"
    hello_world.write_text("""---
title: "Hello World"
tags:
  - test
  - example
---

# Hello World

This is a test page with frontmatter.
""")

    # Create a page without frontmatter
    test_page = en_dir / "test.md"
    test_page.write_text("""# Test Page

This is a test page without frontmatter.
""")

    # Create templates directory
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    # Create article template
    article_template = templates_dir / "article.html"
    article_template.write_text("""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="/web{{ css_path }}">
    <title>{{ title }}</title>
</head>
<body>
<header>
    Test Wiki
</header>
<h1 class="title">{{ title }}</h1>
<article>
  {{ content | safe }}
</article>
<footer>
    v0.0.0
</footer>
</body>
</html>
""")

    # Create index template
    index_template = templates_dir / "index.html"
    index_template.write_text("""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="/web{{ css_path }}">
    <title>{{ title }}</title>
</head>
<body>
<header>
    Test Wiki
</header>
<h1>{{ title }}</h1>
<footer>
    v0.0.0
</footer>
</body>
</html>
""")

    # Create styles directory
    styles_dir = tmp_path / "styles"
    styles_dir.mkdir()

    # Create a simple SCSS file
    index_scss = styles_dir / "index.scss"
    index_scss.write_text("""body {
    font-family: sans-serif;
    margin: 0;
    padding: 20px;
}

header {
    background-color: #333;
    color: white;
    padding: 10px;
}

footer {
    margin-top: 20px;
    padding: 10px;
    border-top: 1px solid #ccc;
}
""")

    yield pages_dir
