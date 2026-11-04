"""GnuPG authenticated encryption with secrets on stdin and an isolated home."""
import os
from pathlib import Path
import subprocess
import tempfile

from .operations_copy import digest


def crypt_file(source, destination, *, executable, key, expected_sha256, decrypt=False, msys_paths=False):
    """Use a separately managed high-entropy key; return no secret diagnostics.

    Decrypt's expected SHA is the trusted plaintext digest. Encrypt's is the
    source digest. Destination must not exist. Existing files are never removed.
    """
    source, destination, executable = map(Path, (source, destination, executable))
    def tool_path(value):
        value = Path(value).resolve().as_posix()
        if msys_paths:
            if os.name != "nt" or len(value) < 3 or value[1:3] != ":/":
                raise ValueError("MSYS paths require a Windows drive path")
            value = "/" + value[0].lower() + value[2:]
        return value
    if not executable.is_absolute() or not executable.is_file():
        raise ValueError("An explicit GnuPG executable is required")
    if not isinstance(key, bytes) or len(key) < 32 or b"\n" in key or b"\r" in key:
        raise ValueError("A separately managed key of at least 32 bytes is required")
    if source.is_symlink() or not source.is_file() or destination.is_symlink():
        raise ValueError("Regular files are required")
    if not decrypt and digest(source) != expected_sha256:
        raise ValueError("Source digest mismatch")
    identity = None
    try:
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        identity = os.fstat(fd)
        with os.fdopen(fd, "wb") as output, tempfile.TemporaryDirectory(prefix="sunjack-gpg-") as home:
            args = [str(executable), "--no-options", "--homedir", tool_path(home), "--batch", "--no-tty",
                    "--pinentry-mode", "loopback", "--passphrase-fd", "0", "--no-symkey-cache"]
            args += ["--decrypt"] if decrypt else ["--symmetric", "--cipher-algo", "AES256", "--compress-algo", "none"]
            # Ciphertext or plaintext goes only to our exclusive file descriptor.
            result = subprocess.run([*args, "--output", "-", "--", tool_path(source)],
                                    input=key + b"\n", stdout=output, stderr=subprocess.PIPE, timeout=300)
            if result.returncode:
                raise RuntimeError("GnuPG operation failed; output not accepted")
            output.flush()
            os.fsync(output.fileno())
        if decrypt and digest(destination) != expected_sha256:
            raise ValueError("Decrypted plaintext digest mismatch")
        if not decrypt and digest(source) != expected_sha256:
            raise ValueError("Source changed during encryption")
        return {"sha256": digest(destination), "bytes": destination.stat().st_size,
                "operation": "decrypt" if decrypt else "encrypt"}
    except Exception as original:
        if identity is not None:
            try:
                current = destination.lstat()
                if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                    destination.unlink()
                else:
                    original.add_note("Cleanup refused: destination identity changed")
            except FileNotFoundError:
                pass
            except OSError as error:
                original.add_note("Crypto cleanup failed: " + type(error).__name__)
        raise
