from src.markdown import _render_markdown


def test_render_heading():
    rendered_html = _render_markdown("""# Hello world!""")

    assert rendered_html == "<h1>Hello world!</h1>"


def test_render_link():
    rendered_html = _render_markdown("""[Hello world!](/hello-world)""")

    assert rendered_html == '<p><a href="/hello-world">Hello world!</a></p>'


def test_render_inline_code():
    rendered_html = _render_markdown("""`inline_code`""")

    assert rendered_html == "<p><code>inline_code</code></p>"
