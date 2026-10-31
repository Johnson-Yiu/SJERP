"""Development settings wrapper that adds only the isolated test identity URL."""

from config.settings import *  # noqa: F401,F403

ROOT_URLCONF = "test_support.isolated_urls"
