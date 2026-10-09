import re
from pathlib import Path

from typer import echo

from app.var import DOTFILES_PATH, LINKS_FILE


class Link:
    def __init__(self, source: Path, target: Path):
        if not source.is_relative_to(DOTFILES_PATH):
            raise Exception(f"Source file {source} must be inside dotfiles directory")
        if target.is_relative_to(DOTFILES_PATH):
            raise Exception(f"Target file {target} cannot be inside dotfiles directory")

        self.source = source
        self.target = target

    def __hash__(self):
        return hash((self.source, self.target))

    def __eq__(self, other):
        if not isinstance(other, Link):
            return False
        return (self.source == other.source) and (self.target == other.target)

    def __str__(self):
        target = (
            str(self.target.resolve())
            if not self.target.relative_to(Path.home())
            else f"$HOME/{self.target.relative_to(Path.home())}"
        )

        return f"{self.source.relative_to(DOTFILES_PATH)} -> {target}"


def read_links() -> list[Link]:
    if not LINKS_FILE.exists():
        return []

    links = []
    with open(LINKS_FILE, "r") as f:
        for i, line in enumerate(f.readlines()):
            match = re.match(r"(.*) -> (.*)", line)
            if not match:
                raise Exception(f"Failed to parse line {i}. {line}")

            source = DOTFILES_PATH / Path(match.group(1))

            target_str = match.group(2)
            if target_str.startswith("$HOME/") or target_str.startswith("~"):
                target = Path.home() / Path(
                    target_str.removeprefix("$HOME/").removeprefix("~/")
                )
            else:
                target = Path(target_str)

            if not source.exists():
                echo(f"Warning: Line {i}: File {source} does not exist.")
            if not target.is_absolute():
                echo(
                    f"Warning: Line {i}: Target is not absolute. This may cause unexpected behavior."
                )

            links.append(Link(source, target))

    return links


def append_link(link: Link):
    with open(LINKS_FILE, "a") as f:
        f.write(str(link) + "\n")


def write_links(links: list[Link]):
    with open(LINKS_FILE, "w") as f:
        for link in links:
            f.write(str(link) + "\n")
