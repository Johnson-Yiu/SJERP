"""Signed evidence produced only after decrypting and restoring an archive.

The signing key must be held by the independent recovery operator; retention
receives only its pinned public key. A writable receipt/config is not trust.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

from .operations_copy import digest
from .operations_crypto import crypt_file


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _openssl(executable, *arguments, data=None):
    executable = Path(executable)
    if not executable.is_absolute() or executable.is_symlink() or not executable.is_file():
        raise ValueError("Explicit trusted OpenSSL executable required")
    result = subprocess.run([str(executable), *map(str, arguments)], input=data,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if result.returncode:
        raise ValueError("Receipt signature operation failed")
    return result.stdout


def public_key_fingerprint(executable, public_key):
    public_key = Path(public_key)
    if not public_key.is_absolute() or public_key.is_symlink() or not public_key.is_file():
        raise ValueError("A separately provisioned public key is required")
    return hashlib.sha256(_openssl(executable, "pkey", "-pubin", "-in", public_key, "-outform", "DER")).hexdigest()


def verify_receipt(receipt, *, encrypted_sha256, executable, public_key, pinned_fingerprint, max_age_seconds, now=None):
    if not isinstance(receipt, dict) or set(receipt) != {"payload", "signature"}:
        raise ValueError("Signed restore receipt is required")
    if type(max_age_seconds) is not int or not 0 < max_age_seconds <= 366 * 86400:
        raise ValueError("Invalid maximum receipt age")
    if not re.fullmatch(r"[0-9a-f]{64}", pinned_fingerprint or "") or public_key_fingerprint(executable, public_key) != pinned_fingerprint:
        raise ValueError("Receipt verification key does not match its trusted pin")
    payload = receipt["payload"]
    if not isinstance(payload, dict) or set(payload) != {"version", "cipher_sha256", "plaintext_sha256", "app_sha", "source_system_identifier", "target_system_identifier", "restored_database", "verified_at", "archive_mtime_ns", "audit_truncate_rejected"}:
        raise ValueError("Invalid receipt fields")
    if payload["version"] != 1 or payload["cipher_sha256"] != encrypted_sha256 or payload["audit_truncate_rejected"] is not True:
        raise ValueError("Receipt does not certify this archive and audit verification")
    if type(payload["archive_mtime_ns"]) is not int or payload["archive_mtime_ns"] <= 0:
        raise ValueError("Invalid observed archive timestamp")
    if not re.fullmatch(r"[0-9a-f]{64}", payload["plaintext_sha256"]) or not re.fullmatch(r"[0-9a-f]{40}", payload["app_sha"]) or not str(payload["source_system_identifier"]).isdecimal() or not str(payload["target_system_identifier"]).isdecimal() or not re.fullmatch(r"sunjack_restore_[0-9a-f]{32}", payload["restored_database"]):
        raise ValueError("Invalid restore provenance")
    verified_at = datetime.fromisoformat(payload["verified_at"])
    now = now or datetime.now(timezone.utc)
    if verified_at.tzinfo is None or verified_at > now or (now - verified_at).total_seconds() > max_age_seconds:
        raise ValueError("Receipt is expired or has an invalid timestamp")
    try:
        signature = base64.b64decode(receipt["signature"], validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("Invalid receipt signature encoding") from error
    if not 32 <= len(signature) <= 1024:
        raise ValueError("Invalid receipt signature size")
    with tempfile.TemporaryDirectory(prefix="sunjack-receipt-") as folder:
        signature_file = Path(folder) / "signature"
        signature_file.write_bytes(signature)
        _openssl(executable, "dgst", "-sha256", "-verify", public_key, "-signature", signature_file, data=_canonical(payload))
    return payload


def restore_and_sign(service, *, encrypted_archive, encrypted_sha256, plaintext_sha256, media_parent,
                     gpg_executable, encryption_key, openssl_executable, signing_key, msys_paths=False):
    """Real decrypt and restore must finish before any receipt can be signed."""
    encrypted_archive = Path(encrypted_archive)
    signing_key = Path(signing_key)
    if encrypted_archive.is_symlink() or not encrypted_archive.is_file() or digest(encrypted_archive) != encrypted_sha256:
        raise ValueError("Encrypted archive digest mismatch")
    if not signing_key.is_absolute() or signing_key.is_symlink() or not signing_key.is_file():
        raise ValueError("Independent protected signing key required")
    if encrypted_archive.parent.resolve() in signing_key.resolve().parents:
        raise ValueError("Signing key must not be stored with backups")
    if os.name == "posix" and signing_key.stat().st_mode & 0o077:
        raise ValueError("Signing key must not be accessible to group or others")
    observed = encrypted_archive.stat()
    temporary = tempfile.TemporaryDirectory(prefix="sunjack-recovery-receipt-")
    restored = None
    primary = None
    try:
        plaintext = Path(temporary.name) / "archive.zip"
        crypt_file(encrypted_archive, plaintext, executable=gpg_executable, key=encryption_key,
                   expected_sha256=plaintext_sha256, decrypt=True, msys_paths=msys_paths)
        with zipfile.ZipFile(plaintext) as bundle:
            entries = [entry for entry in bundle.infolist() if entry.filename == "manifest.json"]
            if len(entries) != 1 or entries[0].file_size > 2 * 1024 * 1024:
                raise ValueError("Archive manifest is missing, duplicated or too large")
            manifest = json.loads(bundle.read(entries[0]))
        restored = service.restore(archive=plaintext, expected_sha256=plaintext_sha256, media_parent=media_parent)
        try:
            if not restored.get("verified") or restored.get("audit_truncate_rejected") is not True:
                raise RuntimeError("Restore and audit verification must complete successfully")
            final_state = encrypted_archive.stat()
            if digest(encrypted_archive) != encrypted_sha256 or (final_state.st_dev, final_state.st_ino, final_state.st_mtime_ns) != (observed.st_dev, observed.st_ino, observed.st_mtime_ns):
                raise RuntimeError("Encrypted archive changed during restore")
            payload = {"version": 1, "cipher_sha256": encrypted_sha256, "plaintext_sha256": plaintext_sha256,
                       "app_sha": manifest["app_sha"], "source_system_identifier": manifest["system_identifier"],
                       "target_system_identifier": service.system_identifier,
                       "archive_mtime_ns": observed.st_mtime_ns,
                       "restored_database": restored["database"], "verified_at": datetime.now(timezone.utc).isoformat(),
                       "audit_truncate_rejected": True}
            signature = _openssl(openssl_executable, "dgst", "-sha256", "-sign", signing_key, data=_canonical(payload))
        except Exception as error:
            error.add_note("Restore target retained for inspection: " + str(restored.get("database", "unknown")))
            raise
    except Exception as error:
        primary = error
        raise
    finally:
        try:
            temporary.cleanup()
        except Exception as cleanup_error:
            detail = "Temporary plaintext cleanup failed: " + type(cleanup_error).__name__
            if restored is not None:
                detail += "; restored target retained: " + str(restored.get("database", "unknown"))
            if primary is not None:
                primary.add_note(detail)
            else:
                cleanup_error.add_note(detail)
                raise
    return {"payload": payload, "signature": base64.b64encode(signature).decode("ascii")}, restored
