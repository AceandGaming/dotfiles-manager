from app.git import Git
from app.var import DOTFILES_PATH

SYMLINKS_FILE = DOTFILES_PATH / ".symlinks"

git = Git(DOTFILES_PATH)


def initialise():
    git.init()
    if not SYMLINKS_FILE.exists():
        SYMLINKS_FILE.touch()
