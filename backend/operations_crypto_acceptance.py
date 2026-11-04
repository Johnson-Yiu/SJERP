"""Real encryption/failure drill using only temporary synthetic resources."""
import argparse
import json
from pathlib import Path
import secrets
import tempfile
import time

from crm.services.operations_crypto import crypt_file
from crm.services.operations_copy import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpg", required=True)
    parser.add_argument("--msys-paths", action="store_true")
    args = parser.parse_args()
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="sunjack-operations-encryption-") as temporary:
        root = Path(temporary)
        source, encrypted, restored = root / "source", root / "encrypted", root / "restored"
        source.write_bytes(b"SYNTHETIC-BACKUP\n" * 65536)
        sha = digest(source)
        key = secrets.token_hex(32).encode()
        options = {"executable": args.gpg, "msys_paths": args.msys_paths, "expected_sha256": sha}
        crypt_file(source, encrypted, key=key, **options)
        crypt_file(encrypted, restored, key=key, decrypt=True, **options)
        assert digest(restored) == sha
        for label, candidate_key, candidate in (("wrong-key", secrets.token_hex(32).encode(), encrypted), ("corrupt", key, root / "damaged")):
            if label == "corrupt":
                candidate.write_bytes(encrypted.read_bytes()[:-50])
            try:
                crypt_file(candidate, root / label, key=candidate_key, decrypt=True, **options)
            except RuntimeError:
                pass
            else:
                raise AssertionError(label + " accepted")
            assert not (root / label).exists()
        result = {"status": "PASS", "bytes": source.stat().st_size, "roundtrip": True,
                  "wrong_key_rejected": True, "corruption_rejected": True,
                  "source_unchanged": digest(source) == sha, "seconds": round(time.monotonic()-start, 3)}
    result["cleanup"] = "complete"
    print(json.dumps(result))


if __name__ == "__main__":
    main()
