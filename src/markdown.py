import html as html_module
import importlib
import re
import logging
import sys
import os

from settings import Settings

settings = Settings()

logger = logging.getLogger(__name__)

# Add current working directory to Python path to allow plugin discovery
# This enables the CLI to find plugins in the directory where it's run
cwd = settings.working_directory or os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)


def _get_impl(module: str, name: str):
    try:
        module = importlib.import_module(module)
        return getattr(module, name, None)
    except ImportError as e:
        logger.info(f"Plugin not found: {module}.{name} - using default implementation")
        logger.debug(f"Import error details: {e}")
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


def _repl_block_code(m):
    language = m.group(1) if m.group(1) else ""
    code = m.group(2)
    # Escape HTML in code content
    code = html_module.escape(code)
    if language:
        return f'<pre><code class="language-{html_module.escape(language)}">{code}</code></pre>'
    return f"<pre><code>{code}</code></pre>"


# Lazy load plugins - cache them after first load
_plugin_cache = {}


def _get_plugin_impl(module: str, name: str, default_impl):
    """Lazily load plugin implementation, falling back to default."""
    cache_key = f"{module}.{name}"

    if cache_key not in _plugin_cache:
        impl = _get_impl(module, name)
        _plugin_cache[cache_key] = impl if impl is not None else default_impl

    return _plugin_cache[cache_key]


def repl_heading(m):
    impl = _get_plugin_impl("plugins.markdown.render", "repl_heading", _repl_heading)
    return impl(m)


def repl_link(m):
    impl = _get_plugin_impl("plugins.markdown.render", "repl_link", _repl_link)
    return impl(m)


def repl_inline_code(m):
    impl = _get_plugin_impl(
        "plugins.markdown.render", "repl_inline_code", _repl_inline_code
    )
    return impl(m)


def repl_block_code(m):
    impl = _get_plugin_impl(
        "plugins.markdown.render", "repl_block_code", _repl_block_code
    )
    return impl(m)


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

    # restore block codes
    for i, match in enumerate(block_codes):
        placeholder = f"__BLOCK_CODE_{i}__"
        text = text.replace(placeholder, repl_block_code(match))

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
