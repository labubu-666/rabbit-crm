import html as html_module
import importlib
import re


def _get_impl(module: str, name: str):
    try:
        module = importlib.import_module(module)
        return getattr(module, name, None)
    except ImportError:
        return None


# headings
def _repl_heading(m):
    level = len(m.group(1))
    content = m.group(2).strip()
    return f"<h{level}>{content}</h{level}>"


def _repl_link(m):
    return f'<a href="{html_module.escape(m.group(2))}">{m.group(1)}</a>'


def _repl_inline_code(m):
    return f"<code>{m.group(1)}</code>"


repl_heading = _get_impl("plugins.markdown.render", "repl_heading") or _repl_heading
repl_link = _get_impl("plugins.markdown.render", "repl_link") or _repl_link
repl_inline_code = (
    _get_impl("plugins.markdown.render", "repl_inline_code") or _repl_inline_code
)


def _render_markdown(text: str) -> str:
    text = html_module.escape(text)

    # headings
    # # title
    text = re.sub(r"^(#{1,6})\s+(.*)$", repl_heading, text, flags=re.M)

    # links
    # [text](url)
    text = re.sub(
        r"\[([^]]+)]\(([^)]+)\)",
        repl_link,
        text,
    )

    # inline code
    # `inline_code`
    text = re.sub(r"`([^`]+)`", repl_inline_code, text)

    # paragraphs: split on two or more newlines
    parts = re.split(r"\n\s*\n", text.strip())
    parts = [p.replace("\n", "<br/>") for p in parts if p.strip()]

    # Don't wrap parts that are already block-level HTML (e.g. headings, lists, pre, blockquote, hr)
    block_start_re = re.compile(
        r"^\s*<(h[1-6]|ul|ol|pre|blockquote|hr|div|table)\b", flags=re.I
    )

    html_parts = []
    for p in parts:
        if block_start_re.match(p):
            html_parts.append(p)
        else:
            html_parts.append(f"<p>{p}</p>")

    html = "".join(html_parts)

    return html
