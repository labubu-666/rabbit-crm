import sys

from pathlib import Path

from logfmter import Logfmter

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import app

import click
import logging
import time

import uvicorn
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from settings import Settings
from build_site import build_site

formatter = Logfmter(keys=["level"], mapping={"level": "levelname"})

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logging.basicConfig(
    handlers=[handler],
    level=logging.DEBUG,
)

logger = logging.getLogger(__name__)


class RebuildHandler(FileSystemEventHandler):
    """File system event handler that triggers site rebuild on changes."""

    def __init__(
        self,
        working_dir: str,
        pages_dir: str,
        dist_dir: str,
        styles_dir: str,
        app_state,
    ):
        self.working_dir = working_dir
        self.pages_dir = pages_dir
        self.dist_dir = dist_dir
        self.styles_dir = styles_dir
        self.app_state = app_state
        self.last_rebuild = 0
        self.debounce_seconds = 1.0  # Debounce to avoid multiple rapid rebuilds

    def on_any_event(self, event):
        """Trigger rebuild on file modification events only."""
        # Ignore directory events
        if event.is_directory:
            return

        # Only respond to actual file modifications, not reads
        # event_type will be 'modified', 'created', 'deleted', 'moved'
        # We want to ignore 'opened', 'closed' events that don't modify files
        from watchdog.events import (
            FileModifiedEvent,
            FileCreatedEvent,
            FileDeletedEvent,
            FileMovedEvent,
        )

        if not isinstance(
            event,
            (FileModifiedEvent, FileCreatedEvent, FileDeletedEvent, FileMovedEvent),
        ):
            return

        # Ignore changes in the dist directory itself
        try:
            event_path = Path(event.src_path)
            dist_path = Path(self.dist_dir).resolve()
            if (
                dist_path in event_path.resolve().parents
                or event_path.resolve() == dist_path
            ):
                return
        except Exception:
            pass

        # Ignore certain files that shouldn't trigger rebuilds
        ignored_files = {".gitignore", ".dist", ".DS_Store"}
        if event_path.name in ignored_files:
            return

        # Debounce: only rebuild if enough time has passed since last rebuild
        current_time = time.time()
        if current_time - self.last_rebuild < self.debounce_seconds:
            return

        logger.info(
            f"Detected change in {Path(event.src_path).resolve()}, rebuilding..."
        )
        try:
            from src.pages import load_pages, compile_and_copy_styles
            from src.search import rebuild_search_index

            settings = Settings()
            Settings.model_validate(settings)

            # Build the static site
            build_site(
                self.working_dir,
                self.pages_dir,
                self.dist_dir,
                self.styles_dir,
                settings,
            )

            # Update app state with new pages
            pages_dir_p = Path(self.pages_dir)
            working_dir_p = Path(self.working_dir)
            dist_dir_p = Path(self.dist_dir)
            styles_dir_p = Path(self.styles_dir)

            logger.info("Reloading pages into app state...")
            pages = load_pages(pages_dir_p, working_dir_p)
            self.app_state.pages = pages
            logger.info(f"Reloaded {len(pages)} page(s) into app state")

            # Recompile styles and update CSS path in app state
            logger.info("Recompiling styles...")
            css_path = compile_and_copy_styles(styles_dir_p, dist_dir_p)
            self.app_state.css_path = css_path
            logger.info(f"Updated CSS path in app state: {css_path}")

            # Rebuild search index with new pages
            logger.info("Rebuilding search index...")
            rebuild_search_index(pages)
            logger.info("Search index rebuilt")

            self.last_rebuild = current_time
            logger.info("Rebuild complete!")
        except Exception as exc:
            logger.error(f"Rebuild failed: {exc}")


@click.group()
def cli():
    """rabbit CLI entrypoint."""
    pass


@cli.command()
@click.option(
    "--working-dir", "working_dir", "-w", default=".", help="Working directory"
)
@click.option(
    "--pages-dir", "pages_dir", "-p", default="pages", help="Path to pages directory"
)
@click.option(
    "--dist-dir", "dist_dir", "-d", default="dist", help="Path to output dist directory"
)
@click.option(
    "--styles-dir",
    "styles_dir",
    "-s",
    default="styles",
    help="Path to styles directory",
)
def build(working_dir: str, pages_dir: str, dist_dir: str, styles_dir: str):
    """Build the site into the dist directory."""
    logger.info("Loading settings.")
    settings = Settings()
    Settings.model_validate(settings)
    logger.info("Loaded settings '%s'.", settings.model_dump())

    # Resolve working_dir first
    working_dir_path = Path(working_dir).resolve()

    # Resolve all paths relative to working_dir
    pages_path = (working_dir_path / pages_dir).resolve()
    dist_path = (working_dir_path / dist_dir).resolve()
    styles_path = (working_dir_path / styles_dir).resolve()

    logger.info(f"Building site from {pages_path} to {dist_path}...")
    build_site(
        str(working_dir_path),
        str(pages_path),
        str(dist_path),
        str(styles_path),
        settings,
    )
    logger.info("Build complete!")


@cli.command()
@click.option(
    "--working-dir", "working_dir", "-w", default=".", help="Working directory"
)
@click.option(
    "--pages-dir", "pages_dir", "-p", default="pages", help="Path to pages directory"
)
@click.option(
    "--dist-dir", "dist_dir", "-d", default="dist", help="Path to output dist directory"
)
@click.option(
    "--styles-dir",
    "styles_dir",
    "-s",
    default="styles",
    help="Path to styles directory",
)
@click.option("--port", "-P", default=8000, help="Port to serve on")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--dev", is_flag=True, help="Enable development mode with live reload")
def serve(
    working_dir: str,
    pages_dir: str,
    dist_dir: str,
    styles_dir: str,
    port: int,
    host: str,
    dev: bool,
):
    """Serve the site from the dist directory. Use --dev for live reload."""
    # Resolve working_dir first
    working_dir_path = Path(working_dir).resolve()

    # Resolve all paths relative to working_dir
    pages_path = (working_dir_path / pages_dir).resolve()
    dist_path = (working_dir_path / dist_dir).resolve()
    styles_path = (working_dir_path / styles_dir).resolve()

    settings = Settings()
    Settings.model_validate(settings)

    # Store paths for startup event
    app.state.working_dir = str(working_dir_path)
    app.state.pages_dir = str(pages_path)
    app.state.dist_dir = str(dist_path)
    app.state.styles_dir = str(styles_path)
    app.state.settings = settings
    app.state.dev_mode = dev

    # In dev mode, build the site and set up file watching
    if dev:
        # Initial build
        logger.info(f"Building site from {pages_path} to {dist_path}...")
        build_site(
            str(working_dir_path),
            str(pages_path),
            str(dist_path),
            str(styles_path),
            settings,
        )
        logger.info("Initial build complete!")
    else:
        # In production mode, check that dist directory exists
        if not dist_path.exists():
            logger.error(
                f"Dist directory '{dist_path}' does not exist. "
                f"Run 'rabbit build' first or use 'rabbit serve --dev' to build and watch."
            )
            sys.exit(1)
        logger.info(f"Serving pre-built site from {dist_path}")

    # Set up file watcher only in dev mode
    observer = None
    if dev:
        event_handler = RebuildHandler(
            str(working_dir_path),
            str(pages_path),
            str(dist_path),
            str(styles_path),
            app.state,
        )
        observer = Observer()
        observer.schedule(event_handler, str(pages_path), recursive=True)
        observer.schedule(event_handler, str(styles_path), recursive=True)
        observer.schedule(
            event_handler, str(working_dir_path / "templates"), recursive=True
        )
        observer.start()
        logger.info(
            f"Watching {pages_path}, {styles_path}, and templates for changes..."
        )

    try:
        logger.info(f"Serving at http://{host}:{port}/web")
        if dev:
            logger.info("Development mode: Live reload enabled")
        logger.info("Press Ctrl+C to stop")
        uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    finally:
        if observer:
            observer.stop()
            observer.join()
        logger.info("Server stopped")


if __name__ == "__main__":
    cli()
