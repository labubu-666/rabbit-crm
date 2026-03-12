import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import click
import logging
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from settings import Settings
from build_site import build_site

logging.basicConfig(
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


class RebuildHandler(FileSystemEventHandler):
    """File system event handler that triggers site rebuild on changes."""

    def __init__(self, pages_dir: str, dist_dir: str, styles_dir: str):
        self.pages_dir = pages_dir
        self.dist_dir = dist_dir
        self.styles_dir = styles_dir
        self.last_rebuild = 0
        self.debounce_seconds = 1.0  # Debounce to avoid multiple rapid rebuilds

    def on_any_event(self, event):
        """Trigger rebuild on any file system event."""
        # Ignore directory events and changes in dist directory
        if event.is_directory:
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

        # Debounce: only rebuild if enough time has passed since last rebuild
        current_time = time.time()
        if current_time - self.last_rebuild < self.debounce_seconds:
            return

        logger.info(f"Detected change in {Path(event.src_path).resolve()}, rebuilding...")
        try:
            settings = Settings()
            Settings.model_validate(settings)
            build_site(self.pages_dir, self.dist_dir, self.styles_dir, settings)
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
    "--pages-dir", "pages_dir", "-p", default="pages", help="Path to pages directory"
)
@click.option(
    "--dist-dir", "dist_dir", "-d", default="dist", help="Path to output dist directory"
)
@click.option(
    "--styles-dir", "styles_dir", "-s", default="styles", help="Path to styles directory"
)
def build(pages_dir: str, dist_dir: str, styles_dir: str):
    """Build the site into the dist directory."""
    logger.info("Loading settings.")
    settings = Settings()
    Settings.model_validate(settings)
    logger.info("Loaded settings '%s'.", settings.model_dump())
    
    logger.info(f"Building site from {Path(pages_dir).resolve()} to {Path(dist_dir).resolve()}...")
    build_site(pages_dir, dist_dir, styles_dir, settings)
    logger.info("Build complete!")


@cli.command()
@click.option(
    "--pages-dir", "pages_dir", "-p", default="pages", help="Path to pages directory"
)
@click.option(
    "--dist-dir", "dist_dir", "-d", default="dist", help="Path to output dist directory"
)
@click.option(
    "--styles-dir", "styles_dir", "-s", default="styles", help="Path to styles directory"
)
@click.option("--port", "-P", default=8000, help="Port to serve on")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
def serve(pages_dir: str, dist_dir: str, styles_dir: str, port: int, host: str):
    """Serve the site and watch for changes, rebuilding when necessary."""
    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import FileResponse, Response

    settings = Settings()
    Settings.model_validate(settings)

    # Initial build with clean flag to remove old files
    logger.info(f"Building site from {Path(pages_dir).resolve()} to {Path(dist_dir).resolve()}...")
    build_site(pages_dir, dist_dir, styles_dir, settings)
    logger.info("Initial build complete!")

    # Set up FastAPI app
    dist_path = Path(dist_dir).resolve()
    app = FastAPI(title="Rabbit Dev Server")

    @app.get("/web/{path:path}")
    async def serve_web(path: str):
        """Serve files from the dist directory with .html extension fallback."""
        if not path:
            path = "index"
        
        file_path = dist_path / path
        
        # If the path exists as-is, serve it
        if file_path.is_file():
            return FileResponse(file_path)
        
        # Try adding .html extension
        html_path = dist_path / f"{path}.html"
        if html_path.is_file():
            return FileResponse(html_path)
        
        # Check for index.html in directory
        if file_path.is_dir():
            index_path = file_path / "index.html"
            if index_path.is_file():
                return FileResponse(index_path)
        
        return Response(content="Not Found", status_code=404)

    @app.get("/web")
    async def serve_web_root():
        """Serve the root index.html."""
        index_path = dist_path / "index.html"
        if index_path.is_file():
            return FileResponse(index_path)
        return Response(content="Not Found", status_code=404)

    # Set up file watcher after initial build to avoid triggering on dist creation
    event_handler = RebuildHandler(pages_dir, dist_dir, styles_dir)
    observer = Observer()
    observer.schedule(event_handler, pages_dir, recursive=True)
    observer.schedule(event_handler, styles_dir, recursive=True)
    observer.start()
    logger.info(f"Watching {Path(pages_dir).resolve()} and {Path(styles_dir).resolve()} for changes...")

    try:
        logger.info(f"Serving at http://{host}:{port}/web")
        logger.info("Press Ctrl+C to stop")
        uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    finally:
        observer.stop()
        observer.join()
        logger.info("Server stopped")


if __name__ == "__main__":
    cli()
