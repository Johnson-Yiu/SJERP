"""Retain test output while removing disposable isolation tokens/connection secrets."""
import re
import sys
from pathlib import Path

source, destination = map(Path, sys.argv[1:3])
text = source.read_text(encoding="utf-8-sig", errors="replace")
patterns = (
    (r"(?i)(['\"](?:token|password|secret_key)['\"]\s*:\s*['\"])[^'\"]+", r"\1[REDACTED]"),
    (r"(/api/__test__/isolation/)[a-f0-9]+", r"\1[REDACTED]"),
    (r"(?i)(postgres(?:ql)?://[^:/\s]+:)[^@\s]+@", r"\1[REDACTED]@"),
)
for pattern, replacement in patterns:
    text = re.sub(pattern, replacement, text)
destination.write_text(text, encoding="utf-8")
