import subprocess
from pathlib import Path


class Git:
    def __init__(self, path: Path):
        self.path = path

    def init(self, branch: str = "main"):
        subprocess.run(["git", "init", "-b", branch], cwd=self.path)

    def add_all(self):
        subprocess.run(["git", "add", "-A"], cwd=self.path)

    def add(self, file: Path):
        subprocess.run(["git", "add", file], cwd=self.path)

    def commit(self, message: str):
        subprocess.run(["git", "commit", "-m", message], cwd=self.path)

    def checkout(self, branch: str):
        subprocess.run(["git", "checkout", branch], cwd=self.path)
