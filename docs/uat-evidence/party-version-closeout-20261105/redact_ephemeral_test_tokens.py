"""Redact only temporary isolation-runner tokens from this evidence directory."""
from pathlib import Path
import re

root = Path(__file__).resolve().parent
patterns = [
    (re.compile(r"(['\"]token['\"]\s*:\s*['\"])[0-9a-f]{48}(['\"])", re.I), r"\1[REDACTED_EPHEMERAL_TOKEN]\2"),
    (re.compile(r"(/api/__test__/isolation/)[0-9a-f]{48}(/)", re.I), r"\1[REDACTED_EPHEMERAL_TOKEN]\2"),
]
changed = 0
for path in root.rglob('*'):
    if not path.is_file() or path.suffix.lower() not in {'.log', '.json', '.txt'}:
        continue
    try:
        original = path.read_text(encoding='utf-8')
    except UnicodeError:
        continue
    result = original
    for pattern, replacement in patterns:
        result = pattern.sub(replacement, result)
    if result != original:
        path.write_text(result, encoding='utf-8', newline='')
        changed += 1
print(f'Redacted ephemeral test tokens in {changed} evidence files.')
