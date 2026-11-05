"""Read-only local availability check; never starts containers or services."""
import base64
import json
import os
import platform
import shutil
import subprocess


def main():
    report = {'platform': platform.platform(), 'python': platform.python_version(),
              'commands': {name: shutil.which(name) for name in ('wsl', 'docker', 'podman', 'setpriv', 'openssl', 'gpg', 'pg_dump', 'pg_restore')}}
    if os.name == 'nt' and report['commands']['wsl']:
        completed = subprocess.run([report['commands']['wsl'], '--list', '--verbose'], capture_output=True, timeout=20)
        raw = completed.stdout + completed.stderr
        report['wsl_list'] = {'exit_code': completed.returncode, 'output_base64': base64.b64encode(raw).decode('ascii'),
                              'output': raw.decode('utf-16le', errors='replace').strip() if b'\0' in raw else raw.decode('mbcs', errors='replace').strip()}
    report['linux_acceptance'] = 'NOT_RUN: availability does not prove isolation, PG17, mount or UID capability'
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
