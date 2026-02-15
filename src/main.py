import click
from src.utils import build_site


@click.group()
def cli():
    """rabbithole CLI entrypoint."""
    pass


@cli.command()
@click.option("--pages-dir", "pages_dir", "-p", default="pages", help="Path to pages directory")
@click.option("--dist-dir", "dist_dir", "-d", default="dist", help="Path to output dist directory")
def build(pages_dir: str, dist_dir: str):
    """Build the site into the dist directory."""
    build_site(pages_dir, dist_dir)


if __name__ == "__main__":
    cli()