import os
from pathlib import Path

from dotenv import load_dotenv

if Path(".env").exists():
    load_dotenv()

DOTFILES_PATH = Path(
    os.environ.get("DOTFILES_PATH", Path.home() / ".dotfiles")
).resolve()

LINKS_FILE = DOTFILES_PATH / ".links"
