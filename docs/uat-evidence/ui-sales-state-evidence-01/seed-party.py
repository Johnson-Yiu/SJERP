"""Create a synthetic quotation and reviewer inside the marked browser-test database."""
import os
from pathlib import Path
import runpy

seed = Path(__file__).resolve().parent.parent / "party-version-closeout-20261105" / "seed_browser.py"
runpy.run_path(str(seed), run_name="__main__")

from django.contrib.auth import get_user_model

get_user_model().objects.create_superuser(
    username="sales-evidence-reviewer", password=os.environ["SALES_EVIDENCE_REVIEWER_PASSWORD"],
)
