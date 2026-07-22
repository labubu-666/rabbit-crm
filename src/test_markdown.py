import pytest

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


def test_render_block_code_without_language():
    rendered_html = _render_markdown("""
```
def hello():
    print("world")
```
""")

    assert (
        rendered_html
        == "<pre><code>def hello():<br/>    print(&quot;world&quot;)<br/></code></pre>"
    )


def test_render_block_code_with_language():
    rendered_html = _render_markdown("""
```python
def hello():
    print("world")
```
""")

    assert (
        rendered_html
        == '<pre><code class="language-python">def hello():<br/>    print(&quot;world&quot;)<br/></code></pre>'
    )


def test_render_block_code_extracts_language():
    """Test that language is correctly extracted from code block"""
    rendered_html = _render_markdown("""
```javascript
console.log("hello");
```
""")

    assert 'class="language-javascript"' in rendered_html
    assert "console.log(&quot;hello&quot;);" in rendered_html


def test_render_block_code_with_backticks():
    """Test that backticks are properly handled in block code"""
    rendered_html = _render_markdown("""
```python
x = 5
```""")

    # Verify the code block is created with pre and code tags
    assert rendered_html.startswith("<pre><code")
    assert rendered_html.endswith("</code></pre>")
    assert "x = 5" in rendered_html


def test_render_block_code_escapes_html():
    """Test that HTML in code blocks is properly escaped"""
    rendered_html = _render_markdown("""
```html
<div>Hello</div>
```""")

    # HTML should be escaped in the code content
    assert "&lt;div&gt;Hello&lt;/div&gt;" in rendered_html
    assert 'class="language-html"' in rendered_html


def test_render_block_code_multiple_blocks():
    """Test multiple code blocks in the same document"""
    rendered_html = _render_markdown("""
```python
print("first")
```

Some text

```javascript
console.log("second");
```""")

    assert 'class="language-python"' in rendered_html
    assert 'class="language-javascript"' in rendered_html
    assert "print(&quot;first&quot;)" in rendered_html
    assert "console.log(&quot;second&quot;);" in rendered_html


def test_render_tab_indented_code():
    """Test that tab-indented code blocks are rendered correctly"""
    rendered_html = _render_markdown("""Some text

\tdef hello():
\t    print("world")

More text""")

    assert "<pre><code>" in rendered_html
    assert "def hello():<br/>    print(&quot;world&quot;)" in rendered_html
    assert "</code></pre>" in rendered_html


def test_render_four_space_indented_code():
    """Test that 4-space indented code blocks are rendered correctly"""
    rendered_html = _render_markdown("""Some text

    def hello():
        print("world")

More text""")

    assert "<pre><code>" in rendered_html
    assert "def hello():<br/>    print(&quot;world&quot;)" in rendered_html
    assert "</code></pre>" in rendered_html


def test_render_tab_indented_code_escapes_html():
    """Test that HTML in tab-indented code blocks is properly escaped"""
    rendered_html = _render_markdown("""
\t<div>Hello</div>
\t<span>World</span>
""")

    assert "&lt;div&gt;Hello&lt;/div&gt;" in rendered_html
    assert "&lt;span&gt;World&lt;/span&gt;" in rendered_html
    assert "<pre><code>" in rendered_html


def test_render_mixed_fenced_and_indented_code():
    """Test that both fenced and indented code blocks work together"""
    rendered_html = _render_markdown("""
```python
print("fenced")
```

Some text

\tprint("indented")

More text""")

    assert 'class="language-python"' in rendered_html
    assert "print(&quot;fenced&quot;)" in rendered_html
    assert "print(&quot;indented&quot;)" in rendered_html
    # Should have two code blocks
    assert rendered_html.count("<pre><code") == 2


def test_render_table():
    rendered_html = _render_markdown("""| Name | Age |
| --- | --- |
| Alice | 31 |
| Bob | 29 |""")

    assert rendered_html == (
        "<table><thead><tr><th>Name</th><th>Age</th></tr></thead>"
        "<tbody><tr><td>Alice</td><td>31</td></tr><tr><td>Bob</td><td>29</td></tr></tbody></table>"
    )


def test_render_table_with_alignment():
    rendered_html = _render_markdown("""| Name | Score | Rank |
| :--- | :---: | ---: |
| Alice | 92 | 1 |""")

    assert rendered_html == (
        '<table><thead><tr><th style="text-align:left">Name</th>'
        '<th style="text-align:center">Score</th><th style="text-align:right">Rank</th></tr></thead>'
        '<tbody><tr><td style="text-align:left">Alice</td>'
        '<td style="text-align:center">92</td><td style="text-align:right">1</td></tr></tbody></table>'
    )


def test_invalid_table_stays_paragraph():
    rendered_html = _render_markdown("""| Name | Age |
| --- |
| Alice | 31 |""")

    assert rendered_html == "<p>| Name | Age |<br/>| --- |<br/>| Alice | 31 |</p>"


@pytest.mark.parametrize(
    "markdown_input,expected_output",
    [
        pytest.param(
            "Check out https://example.com for more info",
            '<p>Check out <a href="https://example.com">https://example.com</a> for more info</p>',
            id="simple_https_url",
        ),
        pytest.param(
            "Visit http://test.org",
            '<p>Visit <a href="http://test.org">http://test.org</a></p>',
            id="simple_http_url",
        ),
        pytest.param(
            "Visit https://example.com and http://test.org",
            '<p>Visit <a href="https://example.com">https://example.com</a> and <a href="http://test.org">http://test.org</a></p>',
            id="multiple_urls",
        ),
        pytest.param(
            "API at https://api.example.com/path?key=value&other=123",
            '<p>API at <a href="https://api.example.com/path?key=value&amp;other=123">https://api.example.com/path?key=value&amp;other=123</a></p>',
            id="url_with_query_params",
        ),
        pytest.param(
            "See https://example.com/docs/guide#section",
            '<p>See <a href="https://example.com/docs/guide#section">https://example.com/docs/guide#section</a></p>',
            id="url_with_path_and_fragment",
        ),
        pytest.param(
            "[Click here](https://example.com)",
            '<p><a href="https://example.com">Click here</a></p>',
            id="markdown_link_not_double_linkified",
        ),
    ],
)
def test_render_linkify(markdown_input, expected_output):
    rendered_html = _render_markdown(markdown_input)
    assert rendered_html == expected_output
