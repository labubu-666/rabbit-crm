import html as html_module
import re

def _render_markdown(md_text: str) -> str:
    text = html_module.escape(md_text)

    # headings
    def _repl_h(m):
        level = len(m.group(1))
        content = m.group(2).strip()
        return f"<h{level}>{content}</h{level}>"
    text = re.sub(r'^(#{1,6})\s+(.*)$', _repl_h, text, flags=re.M)

    # links [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f"<a href=\"{html_module.escape(m.group(2))}\">{m.group(1)}</a>", text)

    # paragraphs: split on two or more newlines
    parts = re.split(r"\n\s*\n", text.strip())
    parts = [p.replace('\n', '<br/>') for p in parts if p.strip()]

    # Don't wrap parts that are already block-level HTML (e.g. headings, lists, pre, blockquote, hr)
    block_start_re = re.compile(r"^\s*<(h[1-6]|ul|ol|pre|blockquote|hr|div|table)\b", flags=re.I)

    html_parts = []
    for p in parts:
        if block_start_re.match(p):
            html_parts.append(p)
        else:
            html_parts.append(f"<p>{p}</p>")

    html = "".join(html_parts)

    return html
