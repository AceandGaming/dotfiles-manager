import json
import re
from pathlib import Path
from typing import TypedDict

from typer import echo

from app.var import DOTFILES_PATH, LINKS_FILE, OLD_LINKS_FILE


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

    def __repr__(self):
        target = (
            str(self.target.resolve())
            if not self.target.relative_to(Path.home())
            else f"$HOME/{self.target.relative_to(Path.home())}"
        )

        return f"{self.source.relative_to(DOTFILES_PATH)} -> {target}"

    def to_dict(self):
        target = (
            str(self.target.resolve())
            if not self.target.relative_to(Path.home())
            else f"$HOME/{self.target.relative_to(Path.home())}"
        )

        return {
            "source": str(self.source.relative_to(DOTFILES_PATH)),
            "target": target,
        }

    @staticmethod
    def from_dict(dict):
        target_str = dict["target"]
        if target_str.startswith("$HOME/") or target_str.startswith("~"):
            target = Path.home() / Path(
                target_str.removeprefix("$HOME/").removeprefix("~/")
            )
        else:
            target = Path(target_str)

        return Link(source=DOTFILES_PATH / dict["source"], target=target)


class Profile:
    def __init__(self, name: str, links: list[Link]):
        self.name = name
        self.links = links

    def add_link(self, source: Path, target: Path):
        self.links.append(Link(source=source, target=target))

    def remove_link(self, target: Path):
        self.links = [link for link in self.links if link.target != target]

    def to_dict(self):
        return {
            "name": self.name,
            "links": [link.to_dict() for link in self.links],
        }

    @staticmethod
    def from_dict(dict):
        return Profile(
            name=dict["name"], links=[Link.from_dict(link) for link in dict["links"]]
        )


class LinksFile:
    def __init__(self, profiles: list[Profile]):
        self.profiles = {p.name: p for p in profiles}

    def set_profile(self, profile: Profile):
        self.profiles[profile.name] = profile

    def to_dict(self):
        return {"profiles": [profile.to_dict() for profile in self.profiles.values()]}

    @staticmethod
    def from_dict(dict):
        return LinksFile([Profile.from_dict(profile) for profile in dict["profiles"]])


def read_old_links() -> list[Link]:
    if not OLD_LINKS_FILE.exists():
        return []

    links = []
    with open(OLD_LINKS_FILE, "r") as f:
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


def read_links_file() -> LinksFile:
    with open(LINKS_FILE, "r") as f:
        return LinksFile.from_dict(json.load(f))


def write_links_file(links: LinksFile) -> None:
    with open(LINKS_FILE, "w") as f:
        json.dump(links.to_dict(), f, indent=2)
