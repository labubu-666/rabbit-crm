import html as html_module


def repl_inline_code_default(m):
    return f"<code>{m.group(1)}</code>"


def repl_block_code_default(m):
    language = m.group(1) if m.group(1) else ""
    code = m.group(2)
    code = html_module.escape(code)
    if language:
        return f'<pre><code class="language-{html_module.escape(language)}">{code}</code></pre>'
    return f"<pre><code>{code}</code></pre>"
