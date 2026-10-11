import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class Change:
    path: Path
    type: Literal["add", "remove", "modify"]


class Git:
    def __init__(self, path: Path):
        self.path = path

    def init(self, branch: str = "main"):
        subprocess.run(["git", "init", "-b", branch], cwd=self.path, check=True)

    def add_all(self):
        subprocess.run(["git", "add", "-A"], cwd=self.path, check=True)

    def add(self, file: Path):
        subprocess.run(["git", "add", file], cwd=self.path, check=True)

    def commit(self, message: str):
        subprocess.run(["git", "commit", "-m", message], cwd=self.path, check=True)

    def push(self):
        subprocess.run(["git", "push"], cwd=self.path, check=True)

    def pull(self):
        subprocess.run(["git", "pull", "origin", "main"], cwd=self.path, check=True)

    def get_changes(self) -> list[Change]:
        """Note: Files must be added first"""
        proc = subprocess.run(
            ["git", "status", "--short"], cwd=self.path, capture_output=True, check=True
        )

        changes = []
        for line in proc.stdout.decode("utf-8").splitlines():
            status, file = line.split(maxsplit=1)
            changes.append(
                Change(
                    path=self.path / file,
                    type={"A": "add", "M": "modify", "D": "remove"}[status],  # type: ignore
                )
            )

        return changes

    def run(self, cmds: list[str]):
        return subprocess.run(["git", *cmds], cwd=self.path)

    def generate_commit_name(
        self,
        changes: list[Change],
    ) -> str:
        if not changes:
            return "Update dotfiles"

        # Ignore automatically managed .links files unless they're the only changes.
        filtered = [change for change in changes if change.path.name != ".links.json"]
        if not filtered:
            filtered = changes

        changes = [
            Change(change.path.relative_to(self.path), change.type)
            for change in filtered
        ]

        verbs = {
            "add": "Added",
            "remove": "Removed",
            "modify": "Changed",
        }

        # A single change is always best described specifically.
        if len(changes) == 1:
            change = changes[0]
            return f"{verbs[change.type]} {change.path.as_posix()}"

        # If all changes share an action and parent directory,
        # summarize the directory instead of listing every file.
        types = {change.type for change in changes}
        parents = {change.path.parent for change in changes}

        if len(types) == 1 and len(parents) == 1:
            parent = next(iter(parents))
            if parent != Path("."):
                directory = parent.as_posix()
                verb = verbs[next(iter(types))]
                return f"{verb} {directory} configs"

        # For a small number of changes, list their paths individually.
        if len(changes) <= 3:
            descriptions = [
                f"{verbs[change.type].lower()} {change.path.as_posix()}"
                for change in changes
            ]
            return "; ".join(description.capitalize() for description in descriptions)

        # Otherwise, summarize by the most common action and directory.
        type_counts = Counter(change.type for change in changes)
        dominant_type = type_counts.most_common(1)[0][0]
        verb = verbs[dominant_type]

        directory_counts = Counter(
            change.path.parent for change in changes if change.path.parent != Path(".")
        )

        if directory_counts:
            directory, count = directory_counts.most_common(1)[0]

            # Only use a directory summary when it describes most changes.
            if count >= len(changes) / 2:
                return f"{verb} {directory.as_posix()} configs"

        return f"{verb} dotfiles"
