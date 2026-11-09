import os
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("seed_workspace_tabs.py")), run_name="__main__")

from django.contrib.auth import get_user_model

username = os.environ["ISS055_UI_USERNAME"]
password = os.environ["ISS055_UI_PASSWORD"]
codex_mode = os.getenv("ISOLATED_CODEX_TEST_SUPERADMIN") == "1"
for name in ((f"{username}-second",) if codex_mode else (username, f"{username}-second")):
    get_user_model().objects.create_superuser(
        username=name, password=password, first_name="codex" if codex_mode else "Workspace integration",
    )
