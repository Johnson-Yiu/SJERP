"""Publish captured output with only expired isolation nonces redacted."""
from pathlib import Path
import re
import zipfile

here = Path(__file__).resolve().parent
with zipfile.ZipFile(here / "published-logs.zip", "w", zipfile.ZIP_DEFLATED) as target:
    for source in sorted(here.glob("*-raw.zip")):
        with zipfile.ZipFile(source) as archive:
            for entry in archive.infolist():
                data = archive.read(entry)
                data = re.sub(rb"(?<![a-f0-9])[a-f0-9]{48}(?![a-f0-9])",
                              b"[ISOLATION_NONCE_REDACTED]", data)
                target.writestr(source.stem + "/" + entry.filename, data)
