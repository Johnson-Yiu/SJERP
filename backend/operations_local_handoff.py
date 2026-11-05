"""Disposable Linux UID handoff drill; it does not perform a database restore.

Run only in a disposable Linux environment as root, with three distinct,
nonzero numeric UIDs and a dedicated numeric group supplied on the command
line. No accounts, services, databases or host files are created or changed.
"""
import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--signer-uid', type=int, required=True)
    parser.add_argument('--reader-uid', type=int, required=True)
    parser.add_argument('--other-uid', type=int, required=True)
    parser.add_argument('--group-gid', type=int, required=True)
    args = parser.parse_args()
    ids = (args.signer_uid, args.reader_uid, args.other_uid)
    if platform.system() != 'Linux' or os.geteuid() != 0 or min(*ids, args.group_gid) <= 0 or len(set(ids)) != 3:
        raise SystemExit('BLOCKED: requires Linux root and three distinct nonzero UIDs plus a nonzero dedicated GID')
    if os.environ.get('SUNJACK_DISPOSABLE_LINUX') != 'yes':
        raise SystemExit('BLOCKED: set SUNJACK_DISPOSABLE_LINUX=yes only in an isolated disposable environment')
    setpriv, openssl = shutil.which('setpriv'), shutil.which('openssl')
    if not setpriv or not openssl:
        raise SystemExit('BLOCKED: setpriv and openssl are required')
    backend = Path(__file__).resolve().parent
    env = {**os.environ, 'PYTHONPATH': str(backend)}
    def run(uid, groups, *cmd, check=True):
        result = subprocess.run([setpriv, '--reuid', str(uid), '--regid', str(args.group_gid),
                                 '--groups' if groups else '--clear-groups', *([str(args.group_gid)] if groups else []),
                                 *map(str, cmd)], env=env, capture_output=True, text=True)
        if check and result.returncode:
            raise RuntimeError('Isolated subprocess failed: ' + result.stderr[-1000:])
        return result
    with tempfile.TemporaryDirectory(prefix='sunjack-handoff-') as name:
        root = Path(name)
        root.chmod(0o755)
        shared, secret = root / 'shared', root / 'secret'
        shared.mkdir(); secret.mkdir()
        os.chown(shared, args.signer_uid, args.group_gid); shared.chmod(0o2750)
        os.chown(secret, args.signer_uid, args.group_gid); secret.chmod(0o700)
        private, public = secret / 'private.pem', root / 'public.pem'
        run(args.signer_uid, True, openssl, 'genpkey', '-algorithm', 'EC', '-pkeyopt', 'ec_paramgen_curve:P-256', '-out', private)
        run(args.signer_uid, True, 'chmod', '600', private)
        pub = run(args.signer_uid, True, openssl, 'pkey', '-in', private, '-pubout').stdout
        public.write_text(pub, encoding='ascii'); public.chmod(0o644)
        # The synthetic signature tests file handoff only; it is not a restore receipt.
        data = root / 'synthetic-message'; data.write_bytes(b'SUNJACK synthetic handoff only\n'); data.chmod(0o644)
        signature = shared / 'signature'
        run(args.signer_uid, True, openssl, 'dgst', '-sha256', '-sign', private, '-out', signature, data)
        code = ('from pathlib import Path; from crm.services.operations_receipt import publish_receipt_file; '
                'import sys; publish_receipt_file(Path(sys.argv[1]), Path(sys.argv[2]).read_bytes(), '
                'group_gid=int(sys.argv[3]) if sys.argv[3] != "none" else None)')
        default, group = shared / 'default.receipt', shared / 'group.receipt'
        run(args.signer_uid, True, sys.executable, '-c', code, default, signature, 'none')
        run(args.signer_uid, True, sys.executable, '-c', code, group, signature, str(args.group_gid))
        assert default.stat().st_mode & 0o777 == 0o600 and group.stat().st_mode & 0o777 == 0o640
        assert run(args.reader_uid, True, 'cat', default, check=False).returncode != 0
        run(args.reader_uid, True, openssl, 'dgst', '-sha256', '-verify', public, '-signature', group, data)
        assert run(args.reader_uid, True, 'sh', '-c', 'printf x >> "$1"', 'sh', group, check=False).returncode != 0
        # Use a different primary GID so the outsider is not accidentally a member.
        outsider = subprocess.run([setpriv, '--reuid', str(args.other_uid), '--regid', str(args.other_uid),
                                   '--clear-groups', 'cat', str(group)], capture_output=True)
        assert outsider.returncode != 0
        assert run(args.reader_uid, True, 'cat', private, check=False).returncode != 0
        failed = run(args.signer_uid, True, sys.executable, '-c', code, group, signature, str(args.group_gid), check=False)
        assert failed.returncode != 0 and not list(shared.glob('.sunjack-receipt-*.partial'))
        print('PASS: synthetic signature handoff; 0600 denied; 0640 read/verify; write/outsider/private-key denied; existing target preserved')
        print('NOT TESTED: database restore, authentic recovery receipt and retention/monitor chain')


if __name__ == '__main__':
    main()
