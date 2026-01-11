from __future__ import annotations

import os


def is_admin_user(user) -> bool:
    """
    Determine whether a user should be treated as an admin.

    Rules (in priority order):
    - If ADMIN_USERNAME is set (non-empty), that username is admin.
    - If ADMIN_USER_IDS is set (comma-separated ints), those ids are admins.
    - Backwards-compatible fallback: when neither is configured, user id == 1 is admin.
    """

    if user is None:
        return False

    admin_username_env = os.getenv("ADMIN_USERNAME")
    admin_username_value = (admin_username_env or "").strip()
    admin_username = admin_username_value or "admin"

    admin_user_ids_raw = (os.getenv("ADMIN_USER_IDS") or "").strip()
    admin_user_ids = set()
    if admin_user_ids_raw:
        for part in admin_user_ids_raw.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                admin_user_ids.add(int(part))
            except ValueError:
                continue

    has_explicit_admin_config = bool(admin_username_value) or bool(admin_user_ids_raw)

    try:
        if getattr(user, "username", None) == admin_username:
            return True
    except Exception:
        pass

    try:
        if getattr(user, "id", None) in admin_user_ids:
            return True
    except Exception:
        pass

    try:
        if not has_explicit_admin_config and getattr(user, "id", None) == 1:
            return True
    except Exception:
        pass

    return False
