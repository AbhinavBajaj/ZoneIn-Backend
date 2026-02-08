"""Default avatar URL for users without a custom avatar (hosted monkey images)."""
from uuid import UUID

# 12 monkey avatars in FE public/avatars/; path is relative so it works for any origin (prod + local)
DEFAULT_AVATAR_COUNT = 12


def default_avatar_url_for_user(user_id: UUID) -> str:
    """Return relative path to a deterministic default monkey avatar (1-12) for this user."""
    index = (user_id.int % DEFAULT_AVATAR_COUNT) + 1
    return f"/avatars/monkey-{index}.png"
