"""Settings selector.

`DJANGO_ENV` picks the overlay: "dev" (default) or "prod".
DJANGO_SETTINGS_MODULE stays `lessonixapp.settings` everywhere.
"""
import os

_env = os.environ.get("DJANGO_ENV", "dev").lower()

if _env in ("prod", "production"):
    from .prod import *  # noqa: F401,F403
else:
    from .dev import *  # noqa: F401,F403
