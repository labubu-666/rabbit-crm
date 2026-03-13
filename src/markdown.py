import html as html_module
import importlib
import re
import logging
import sys
import os

logger = logging.getLogger(__name__)

# Add current working directory to Python path to allow plugin discovery
# This enables the CLI to find plugins in the directory where it's run
cwd = os.getcwd()
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
