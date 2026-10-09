import os
from pathlib import Path

import typer

import app.file as file
from app.git import Git
from app.var import DOTFILES_PATH, LINKS_FILE

app = typer.Typer(add_completion=False)
git = Git(DOTFILES_PATH)

previous_links: list[file.Link] = []


def check_dotfiles_path():
    if not DOTFILES_PATH.exists() or not LINKS_FILE.exists():
        typer.echo("Error: dotfiles directory does not exist or is invaild")
        typer.echo("Hint: Use `init` to initialize the dotfiles directory")
        raise typer.Exit(1)


@app.command("path")
def c_get_path():
    """Get the path to the dotfiles directory"""
    typer.echo(DOTFILES_PATH.absolute())


@app.command("update")
def c_update():
    if not LINKS_FILE.exists():
        LINKS_FILE.touch()

    typer.echo("Reading symlinks...")
    links = file.read_links()

    typer.echo("Creating file links...")
    for link in links:
        if not link.source.exists():
            typer.echo(f"Warning: source file does not exist: {link.source}")
            continue

        if link.target.exists():
            if link.source.samefile(link.target):
                continue
            link.target.unlink()

        typer.echo(f"Linking {link.source} -> {link.target}")
        os.link(link.source, link.target)

    typer.echo("Done!")


@app.command("init")
def c_init():
    DOTFILES_PATH.mkdir(parents=True, exist_ok=True)
    git.init()
    if not LINKS_FILE.exists():
        LINKS_FILE.touch()

    git.add(LINKS_FILE)
    git.commit("Initial commit")


@app.command("link")
def c_link_file(source: Path, target: Path):
    """Link a config file to a target path"""
    check_dotfiles_path()

    source = source.resolve()
    target = target.resolve()

    if not source.is_file():
        raise typer.BadParameter(f"File not found: {source}")
    if not source.is_relative_to(DOTFILES_PATH):
        raise typer.BadParameter(
            f"Source file {source} must be inside dotfiles directory"
        )
    if target.is_relative_to(DOTFILES_PATH):
        raise typer.BadParameter(
            f"Target file {target} cannot be inside dotfiles directory"
        )

    if target.exists():
        if not typer.confirm(f"Target file {target} already exists. Add anyway?"):
            raise typer.Abort()

    links = file.read_links()
    for link in links:
        if link.target == target:
            raise typer.BadParameter(f"Config with target {target} already exists")

    file.append_link(file.Link(source, target))


@app.command("unlink")
def c_unlick_file(target: Path):
    """Remove a link"""
    check_dotfiles_path()

    target = target.resolve()

    links = file.read_links()
    for link in links:
        if link.target == target:
            links.remove(link)

    file.write_links(links)

    if not target.exists():
        return

    if typer.confirm("Also remove file?"):
        target.unlink()


@app.command("add")
def c_add_file(
    config_path: Path,
    dotfiles_path: Path,
    remove_existing: bool = typer.Option(
        False,
        "--move",
        "--no-link",
        "-m",
        help="Move file to dotfiles instead of linking them",
    ),
):
    """Add a existing config to dotfiles"""
    check_dotfiles_path()

    source = config_path.resolve()
    target = dotfiles_path.resolve()

    if not source.is_file():
        raise typer.BadParameter(f"File not found: {source}")
    if source.is_relative_to(DOTFILES_PATH):
        raise typer.BadParameter(
            f"Config file {source}  cannot be inside dotfiles directory"
        )
    if target.is_relative_to(DOTFILES_PATH):
        raise typer.BadParameter(
            f"Dotfiles file {target} must be inside dotfiles directory"
        )
    if target.exists():
        raise typer.BadParameter(f"File already exists: {target}")

    file.append_link(file.Link(target, source))
    os.link(source, target)

    if remove_existing:
        source.unlink()


@app.command("checkout")
def c_checkout(branch: str = typer.Argument("main", help="Branch name of git repo")):
    check_dotfiles_path()

    git.checkout(branch)


def main():
    app()
