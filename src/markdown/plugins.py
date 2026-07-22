import importlib
import logging
import os
import sys

from settings import Settings

from .code import repl_block_code_default, repl_inline_code_default
from .headings import repl_heading_default
from .links import repl_link_default

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


_plugin_cache = {}


def _get_plugin_impl(module: str, name: str, default_impl):
    """Lazily load plugin implementation, falling back to default."""
    cache_key = f"{module}.{name}"

    if cache_key not in _plugin_cache:
        impl = _get_impl(module, name)
        _plugin_cache[cache_key] = impl if impl is not None else default_impl

    return _plugin_cache[cache_key]


def repl_heading(m):
    impl = _get_plugin_impl(
        "plugins.markdown.render", "repl_heading", repl_heading_default
    )
    return impl(m)


def repl_link(m):
    impl = _get_plugin_impl("plugins.markdown.render", "repl_link", repl_link_default)
    return impl(m)


def repl_inline_code(m):
    impl = _get_plugin_impl(
        "plugins.markdown.render", "repl_inline_code", repl_inline_code_default
    )
    return impl(m)


def repl_block_code(m):
    impl = _get_plugin_impl(
        "plugins.markdown.render", "repl_block_code", repl_block_code_default
    )
    return impl(m)
