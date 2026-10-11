import os
from pathlib import Path
from subprocess import CalledProcessError

import typer

import app.file as file
from app.git import Git
from app.var import DOTFILES_PATH, LINKS_FILE

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)
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
def c_update(
    override: bool | None = typer.Option(
        None,
        "--override",
        "-y/-n",
        help="Override existing configs with ones in dotfiles",
    ),
    pull: bool = typer.Option(False, "--pull", help="Pull from origin (if set)"),
    commit: bool = typer.Option(
        True, "--commit/--no-commit", help="Automatically create a git commit"
    ),
    push_commit: bool = typer.Option(False, "--push", help="Push to origin (if set)"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    check_dotfiles_path()

    if pull:
        if dry_run:
            typer.echo("[DRY RUN] Would pull from origin")
        else:
            typer.echo("Pulling from origin...")
            try:
                git.pull()
            except CalledProcessError:
                typer.echo("Error: failed to pull from origin", err=True)
                raise typer.Exit(1)

    typer.echo("Reading .links file...")
    links = file.read_links()

    typer.echo("Creating file links...")
    for link in links:
        if not link.source.exists():
            typer.echo(f"Warning: source file does not exist: {link.source}")
            continue

        if link.target.exists() or link.target.is_symlink():
            if link.source.samefile(link.target):
                continue

            if override is None:
                message = f"Target file {link.target} already exists. Override?"

                if dry_run:
                    message += " (dry run; file will not be modified)"

                override = typer.confirm(message)

            if override:
                if dry_run:
                    typer.echo(f"[DRY RUN] Would unlink {link.target}")
                else:
                    link.target.unlink()
            else:
                continue

        if dry_run:
            if not link.target.parent.exists():
                typer.echo(
                    f"[DRY RUN] Would create parent directory {link.target.parent}"
                )
            typer.echo(f"[DRY RUN] Would link {link.source} -> {link.target}")
        else:
            typer.echo(f"Linking {link.source} -> {link.target}")
            link.target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(link.source, link.target)
            except OSError:
                typer.echo(f"Error: failed to link {link.source} -> {link.target}")

    if commit:
        git.add_all()

        changes = git.get_changes()
        if len(changes) == 0:
            typer.echo("No changes to commit")
        else:
            typer.echo(f"Found {len(changes)} changes")

            name = git.generate_commit_name(changes)
            if dry_run:
                typer.echo(f"[DRY RUN] Would commit: {name}")
            else:
                typer.echo(f"Creating commit: {name}")
                git.commit(name)

            if push_commit:
                if dry_run:
                    typer.echo("[DRY RUN] Would push to origin")
                else:
                    typer.echo("Pushing commit")
                    git.push()

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

    source = (DOTFILES_PATH / source).resolve()
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

    links = file.read_links()
    for link in links:
        if link.target == target:
            raise typer.BadParameter(f"Config with target {target} already exists")

    if target.exists():
        typer.echo("Warning: Target file already exists")

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
        "-m",
        help="Move file to dotfiles instead of linking them",
    ),
    create_parents: bool = typer.Option(
        False,
        "--create-parents",
        "-p",
    ),
):
    """Add an existing config to dotfiles"""
    check_dotfiles_path()

    config_path = config_path.resolve()
    dotfiles_path = (DOTFILES_PATH / dotfiles_path).resolve()

    if not config_path.is_file():
        raise typer.BadParameter(f"File not found: {dotfiles_path}")
    if config_path.is_relative_to(DOTFILES_PATH):
        raise typer.BadParameter(
            f"Config file {config_path}  cannot be inside dotfiles directory"
        )
    if not dotfiles_path.is_relative_to(DOTFILES_PATH):
        raise typer.BadParameter(
            f"Dotfile {dotfiles_path} must be inside dotfiles directory"
        )
    if dotfiles_path.exists():
        raise typer.BadParameter(f"File already exists: {dotfiles_path}")

    if create_parents:
        dotfiles_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        if not dotfiles_path.parent.exists():
            raise typer.BadParameter(
                f"Parent directory does not exist: {dotfiles_path.parent}.\nHint: Use -p to create it"
            )

    os.link(config_path, dotfiles_path)

    if remove_existing:
        config_path.unlink()
    else:
        file.append_link(file.Link(dotfiles_path, config_path))


@app.command(
    "git", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def c_git(ctx: typer.Context):
    """Run any git command in the dotfiles directory"""
    check_dotfiles_path()
    proc = git.run(list(ctx.args))
    raise typer.Exit(code=proc.returncode)


def main():
    app()
