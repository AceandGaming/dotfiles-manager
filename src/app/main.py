import os
from pathlib import Path
from subprocess import CalledProcessError

import typer

import app.file as file
from app.git import Git
from app.state import state
from app.var import DOTFILES_PATH, LINKS_FILE, OLD_LINKS_FILE

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)
git = Git(DOTFILES_PATH)

previous_links: list[file.Link] = []


def check_dotfiles_path():
    if not DOTFILES_PATH.exists() or not LINKS_FILE.exists():
        typer.echo("Error: dotfiles directory does not exist or is invaild")
        if OLD_LINKS_FILE.exists():
            typer.echo("Hint: Use `migrate` to migrate the existing .links file")
        else:
            typer.echo("Hint: Use `init` to initialize the dotfiles directory")
        raise typer.Exit(1)


def get_profile(profile_name: str | None = None):
    if profile_name is None:
        profile_name = state.profile

    links_file = file.read_links_file()
    if profile_name not in links_file.profiles:
        return file.Profile(profile_name, []), links_file

    return links_file.profiles[profile_name], links_file


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

    typer.echo("Reading links file...")
    global_profile, _ = get_profile("global")
    profile, _ = get_profile()

    links = profile.links + global_profile.links

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

    profile, f = get_profile()
    for link in profile.links:
        if link.target == target:
            raise typer.BadParameter(f"Config with target {target} already exists")

    if target.exists():
        typer.echo("Warning: Target file already exists")

    profile.add_link(source, target)

    f.set_profile(profile)
    file.write_links_file(f)


@app.command("unlink")
def c_unlink_file(target: Path):
    """Remove a link"""
    check_dotfiles_path()

    target = target.resolve()

    profile, f = get_profile()
    profile.remove_link(target)
    f.set_profile(profile)
    file.write_links_file(f)

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
    profile_name: str | None = typer.Option(None, "--profile"),
):
    """Add an existing config to dotfiles"""
    check_dotfiles_path()

    if profile_name is None:
        profile_name = state.profile

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
        profile, f = get_profile(profile_name)
        profile.add_link(dotfiles_path, config_path)
        f.set_profile(profile)
        file.write_links_file(f)


@app.command(
    "git", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def c_git(ctx: typer.Context):
    """Run any git command in the dotfiles directory"""
    check_dotfiles_path()
    proc = git.run(list(ctx.args))
    raise typer.Exit(code=proc.returncode)


@app.command("profile")
def c_set_profile(profile: str = typer.Argument("global")):
    """Switches the current profile"""
    check_dotfiles_path()
    state.profile = profile

    typer.echo(f"Switched to profile {profile}")
    typer.echo("Use `doty update` to apply the new profile")


@app.command("migrate")
def c_migrate():
    if not OLD_LINKS_FILE.exists():
        typer.echo("No file to migrate")
        return
    if LINKS_FILE.exists():
        typer.echo("Links file already exists", err=True)
        raise typer.Exit(1)

    links = file.read_old_links()
    profile = file.Profile(name="global", links=links)

    file.write_links_file(file.LinksFile(profiles=[profile]))

    typer.echo("Migrated!")
    if typer.confirm("Do you want to remove the old links file?"):
        OLD_LINKS_FILE.unlink()


def main():
    app()
