"""In-memory OAuth state store (no sessions)."""
import time

_store: dict[str, tuple[float, str | None]] = {}
_TTL_SEC = 600  # 10 min


def set_state(state: str, redirect_ui: str | None = None) -> None:
    _store[state] = (time.monotonic(), redirect_ui)


def check_state(state: str) -> tuple[bool, str | None]:
    if state not in _store:
        return False, None
    ts, redirect_ui = _store[state]
    del _store[state]
    if time.monotonic() - ts > _TTL_SEC:
        return False, None
    return True, redirect_ui
