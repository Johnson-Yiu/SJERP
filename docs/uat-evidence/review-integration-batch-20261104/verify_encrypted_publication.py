"""Real GPG publication check using a previously verified synthetic PG archive."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sys
import tempfile

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root.parents[2] / "backend"))
from operations_backup import _encrypted_backup
from crm.services.operations_crypto import crypt_file

source = root / "artifacts/postgres-backups/319941c05e46-b453a6b3.zip"
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
executable = Path(sys.argv[1]).resolve(strict=True)


class VerifiedArchive:
    def backup(self, *, media_root, destination):
        # This is not a new PG backup or a maintenance-fence acceptance.
        shutil.copyfile(source, destination)
        return {"sha256": source_sha}


key = secrets.token_hex(32).encode("ascii")
with tempfile.TemporaryDirectory(prefix="sunjack-real-publication-") as folder:
    folder = Path(folder)
    destination = folder / "verified.gpg"
    result = _encrypted_backup(VerifiedArchive(), media_root=None, destination=destination,
                               key=key, encryption={"executable": executable, "msys_paths": os.name == "nt"},
                               crypt_file=crypt_file)
    assert destination.is_file() and result["encryption_roundtrip_verified"]
    assert sorted(path.name for path in folder.iterdir()) == ["verified.gpg"]

    def corrupt_then_decrypt(source_file, target_file, **kwargs):
        if kwargs.get("decrypt"):
            path = Path(source_file)
            raw = bytearray(path.read_bytes())
            raw[-1] ^= 1
            path.write_bytes(raw)
        return crypt_file(source_file, target_file, **kwargs)

    rejected = False
    try:
        _encrypted_backup(VerifiedArchive(), media_root=None, destination=folder / "must-not-publish.gpg",
                          key=key, encryption={"executable": executable, "msys_paths": os.name == "nt"},
                          crypt_file=corrupt_then_decrypt)
    except (ValueError, RuntimeError):
        rejected = True
    assert rejected
    assert sorted(path.name for path in folder.iterdir()) == ["verified.gpg"]
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_sha
print(json.dumps({"status": "PASS", "passed": 2, "failed": 0, "source_archive_sha256": source_sha,
                  "real_gpg_roundtrip": True, "real_corruption_rejected_before_publication": True,
                  "source_unchanged": True, "cleanup": "complete",
                  "scope": "Actual GPG plus publication; input is retained synthetic PG archive, not new maintenance backup"}))
