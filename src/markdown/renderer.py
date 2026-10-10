import html as html_module
import os
import re
import sys

from .plugins import repl_block_code, repl_heading, repl_inline_code, repl_link
from .tables import render_table_block


def _render_markdown(text: str, working_dir: str = None) -> str:
    """Render markdown text to HTML.

    Args:
        text: The markdown text to render
        working_dir: The working directory to use for plugin discovery.
                     If not provided, uses current working directory.
    """
    # Add working directory to Python path to allow plugin discovery
    # This enables the CLI to find plugins in the directory where it's run
    cwd = working_dir or os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    # block code (must be processed before escaping)
    # ```language
    # code
    # ```
    block_code_pattern = r"```(\w+)?\n(.*?)```"
    block_codes = []

    def save_block_code(m):
        placeholder = f"__BLOCK_CODE_{len(block_codes)}__"
        block_codes.append(m)
        return placeholder

    text = re.sub(block_code_pattern, save_block_code, text, flags=re.DOTALL)

    # Tab-indented code blocks (must be processed before escaping)
    # Lines starting with a tab or 4 spaces are treated as code
    # Match one or more consecutive indented lines
    tab_code_pattern = r"(?:^(?:\t|    ).+$\n?)+"

    def save_tab_code(m):
        placeholder = f"__BLOCK_CODE_{len(block_codes)}__"
        # Remove the leading tab or 4 spaces from each line
        code = m.group(0)
        lines = code.split("\n")
        dedented_lines = []
        for line in lines:
            if line.startswith("\t"):
                dedented_lines.append(line[1:])
            elif line.startswith("    "):
                dedented_lines.append(line[4:])
            else:
                dedented_lines.append(line)
        dedented_code = "\n".join(dedented_lines)

        # Create a match-like object with no language (group 1) and the dedented code (group 2)
        class TabCodeMatch:
            def group(self, n):
                if n == 1:
                    return None
                if n == 2:
                    return dedented_code.rstrip("\n")
                return None

        block_codes.append(TabCodeMatch())
        return placeholder

    text = re.sub(tab_code_pattern, save_tab_code, text, flags=re.MULTILINE)

    # Save markdown links before processing linkification
    # [text](url)
    markdown_links = []

    def save_markdown_link(m):
        placeholder = f"__MARKDOWN_LINK_{len(markdown_links)}__"
        markdown_links.append(m)
        return placeholder

    text = re.sub(r"\[([^]]+)]\(([^)]+)\)", save_markdown_link, text)

    text = html_module.escape(text)

    # headings
    # # title
    text = re.sub(r"^(#{1,6})\s+(.*)$", repl_heading, text, flags=re.M)

    # linkify plain URLs (http/https)
    # https://example.com or http://example.com
    text = re.sub(
        r"(?<![\[&\w])https?://[^\s<>\")'`&]+(?:&amp;[^\s<>\")'`&]+)*",
        lambda m: f'<a href="{m.group(0)}">{m.group(0)}</a>',
        text,
    )

    # restore markdown links
    for i, match in enumerate(markdown_links):
        placeholder = f"__MARKDOWN_LINK_{i}__"
        text = text.replace(placeholder, repl_link(match))

    # inline code
    # `inline_code`
    text = re.sub(r"`([^`]+)`", repl_inline_code, text)

    # restore block codes
    for i, match in enumerate(block_codes):
        placeholder = f"__BLOCK_CODE_{i}__"
        text = text.replace(placeholder, repl_block_code(match))

    # paragraphs: split on two or more newlines
    raw_parts = re.split(r"\n\s*\n", text.strip())
    parts = []
    for part in raw_parts:
        if not part.strip():
            continue
        table_html = render_table_block(part)
        if table_html is not None:
            parts.append(table_html)
        else:
            parts.append(part.replace("\n", "<br/>"))

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
