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
