from src.markdown import _render_markdown


def test_render_markdown():
    rendered_html = _render_markdown("""# Hello world!""")

    assert rendered_html == "<h1>Hello world!</h1>"
