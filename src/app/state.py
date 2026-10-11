from app.var import DOTY_STATE

PROFILE_PATH = DOTY_STATE / "current_profile"


class State:
    @property
    def profile(self) -> str:
        if not PROFILE_PATH.exists():
            return "global"
        return PROFILE_PATH.read_text().strip() or "global"

    @profile.setter
    def profile(self, value: str) -> None:
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_PATH.write_text(value)

    def __init__(self) -> None:
        self.profile = self.profile


state = State()
