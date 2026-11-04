"""Archive closed integration logs; redact credential fields, retain result bytes."""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

root = Path(__file__).resolve().parent
excluded = set(sys.argv[1:])
entries = []
target = root / "raw-logs-phase-01.zip"
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted((root / "logs").rglob("*")):
        if not path.is_file() or path.name in excluded:
            continue
        original = path.read_bytes()
        published = original
        redactions = 0
        # CI occasionally prints an ephemeral test key. Keep source logs local;
        # publish an explicitly marked redacted copy, never the secret itself.
        for pattern in (rb"(DJANGO_SECRET_KEY:\s*)(?!\*\*\*|\[REDACTED)[^\s\r\n]+",
                        rb"(?:gho_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})"):
            def replace(match):
                return (match.group(1) if match.lastindex else b"") + b"[REDACTED_TEST_CREDENTIAL]"
            published, count = re.subn(pattern, replace, published)
            redactions += count
        name = path.relative_to(root).as_posix()
        archive.writestr(name, published)
        entries.append({"path": name, "source_sha256": hashlib.sha256(original).hexdigest(),
                        "published_sha256": hashlib.sha256(published).hexdigest(),
                        "bytes": len(published), "credential_redactions": redactions})
manifest = {"archive": target.name, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "scope": "Integration run logs; failed runs retained. Explicit credential redactions only.",
            "excluded_running_logs": sorted(excluded), "entries": entries}
(root / "raw-logs-phase-01-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"files": len(entries), "redactions": sum(x["credential_redactions"] for x in entries),
                  "bytes": target.stat().st_size, "sha256": manifest["sha256"]}))
