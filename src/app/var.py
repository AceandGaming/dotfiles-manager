import os
from pathlib import Path

DOTFILES_PATH = Path(
    os.environ.get("DOTY_DOTFILES_PATH", Path.home() / ".dotfiles")
).resolve()

OLD_LINKS_FILE = DOTFILES_PATH / ".links"
LINKS_FILE = DOTFILES_PATH / ".links.json"

DOTY_STATE = (
    Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "doty"
)
