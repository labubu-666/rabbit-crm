import click
import logging
import http.server
import socketserver
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.utils import build_site

logging.basicConfig(
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


class RebuildHandler(FileSystemEventHandler):
    """File system event handler that triggers site rebuild on changes."""

    def __init__(self, pages_dir: str, dist_dir: str):
        self.pages_dir = pages_dir
        self.dist_dir = dist_dir
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

        logger.info(f"Detected change in {event.src_path}, rebuilding...")
        try:
            build_site(self.pages_dir, self.dist_dir)
            self.last_rebuild = current_time
            logger.info("Rebuild complete!")
        except Exception as exc:
            logger.error(f"Rebuild failed: {exc}")


@click.group()
def cli():
    """rabbithole CLI entrypoint."""
    pass


@cli.command()
@click.option(
    "--pages-dir", "pages_dir", "-p", default="pages", help="Path to pages directory"
)
@click.option(
    "--dist-dir", "dist_dir", "-d", default="dist", help="Path to output dist directory"
)
def build(pages_dir: str, dist_dir: str):
    """Build the site into the dist directory."""
    
    logger.info(f"Building site from {pages_dir} to {dist_dir}...")
    build_site(pages_dir, dist_dir)
    logger.info("Build complete!")


@cli.command()
@click.option(
    "--pages-dir", "pages_dir", "-p", default="pages", help="Path to pages directory"
)
@click.option(
    "--dist-dir", "dist_dir", "-d", default="dist", help="Path to output dist directory"
)
@click.option("--port", "-P", default=8000, help="Port to serve on")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
def serve(pages_dir: str, dist_dir: str, port: int, host: str):
    """Serve the site and watch for changes, rebuilding when necessary."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initial build with clean flag to remove old files
    logger.info(f"Building site from {pages_dir} to {dist_dir}...")
    build_site(pages_dir, dist_dir)
    logger.info("Initial build complete!")

    # Set up HTTP server in the dist directory
    dist_path = Path(dist_dir).resolve()

    class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dist_path), **kwargs)

        def translate_path(self, path):
            """Translate URL path to filesystem path, handling /web prefix."""
            # Remove /web prefix if present
            if path.startswith("/web/"):
                path = path[4:]  # Remove '/web'
            elif path == "/web":
                path = "/"

            # Call parent's translate_path with modified path
            return super().translate_path(path)

        def log_message(self, format, *args):
            # Custom logging format
            logger.info(f"{self.address_string()} - {format % args}")

    # Set up file watcher after initial build to avoid triggering on dist creation
    event_handler = RebuildHandler(pages_dir, dist_dir)
    observer = Observer()
    observer.schedule(event_handler, pages_dir, recursive=True)
    observer.start()
    logger.info(f"Watching {pages_dir} for changes...")

    try:
        class ReusableTCPServer(socketserver.TCPServer):
            allow_reuse_address = True

        with ReusableTCPServer((host, port), CustomHTTPRequestHandler) as httpd:
            logger.info(f"Serving at http://{host}:{port}/web")
            logger.info("Press Ctrl+C to stop")
            httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    finally:
        observer.stop()
        observer.join()
        logger.info("Server stopped")


if __name__ == "__main__":
    cli()
