"""Development settings wrapper that adds only the isolated test identity URL."""

from config.settings import *  # noqa: F401,F403

ROOT_URLCONF = "test_support.isolated_urls"

# Only the dedicated isolated replacement-browser run uses these fixture
# templates.  The seed writes sanitized copies under this run's marked root.
import os
from pathlib import Path
if os.environ.get('ISOLATED_PLAYWRIGHT_TEST_FILE') == 'party-replacement-quote-real.spec.js':
    from crm import quote_template_snapshot
    quote_template_snapshot.PROJECT_ROOT = Path(os.environ['ISOLATED_TEST_ROOT']) / 'synthetic-quote-templates'
