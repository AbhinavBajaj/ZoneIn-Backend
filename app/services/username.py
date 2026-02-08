"""Username generation utilities.

Format: firstname_lastname_N (e.g. abhinav_bajaj_1, mary_nasimova_1).
N is assigned chronologically by the backend so the first user with that
first+last name gets _1, the next _2, etc. No conflicts.
"""
import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def _sanitize_part(part: str) -> str:
    """Lowercase and keep only alphanumeric for a name part."""
    return re.sub(r"[^a-z0-9]", "", part.lower()) if part else ""


def name_to_base(full_name: str | None) -> str:
    """Convert full name to base slug: firstname_lastname.

    - "Abhinav Bajaj" -> "abhinav_bajaj"
    - "Mary Nasimova" -> "mary_nasimova"
    - "Vineeta Bajaj" -> "vineeta_bajaj"
    - Single word -> "word_user" so we have a valid base.
    """
    if not full_name or not full_name.strip():
        return "user_user"
    parts = full_name.strip().split()
    first = _sanitize_part(parts[0]) if parts else "user"
    last = _sanitize_part(parts[1]) if len(parts) > 1 else "user"
    if not first:
        first = "user"
    if not last:
        last = "user"
    return f"{first}_{last}"


def get_next_chronological_number(db: Session, base: str) -> int:
    """Return the next chronological index N for this base (no conflicts).

    Finds existing usernames matching base_N and returns max(N) + 1, or 1 if none.
    """
    import re
    pattern = re.compile(r"^" + re.escape(base) + r"_(\d+)$")
    rows = db.execute(select(User.username).where(User.username.isnot(None))).all()
    max_n = 0
    for (username,) in rows:
        if not username:
            continue
        m = pattern.match(username)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def generate_unique_username(db: Session, full_name: str) -> str:
    """Generate a unique username: firstname_lastname_N.

    N is assigned chronologically (first user with that first+last gets _1, etc.).
    BE ensures no conflicts.
    """
    base = name_to_base(full_name)
    n = get_next_chronological_number(db, base)
    return f"{base}_{n}"
