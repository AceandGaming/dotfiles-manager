import os
from pathlib import Path

DOTFILES_PATH = Path(
    os.environ.get("DOTY_DOTFILES_PATH", Path.home() / ".dotfiles")
).resolve()

LINKS_FILE = DOTFILES_PATH / ".links"
