#!/bin/sh
set -eu
umask 077
[ "$(id -u)" = 0 ] && [ "$(hostname -s)" = sjerp-image-test ] || exit 1
test -r /etc/issue.d/93-sjerp-lan.issue
grep -q '^SJERP LAN GUEST READY:' /etc/issue.d/93-sjerp-lan.issue
systemctl is-active --quiet sjerp-local@a.service
status=/etc/issue.d/94-sjerp-business.issue
report() { printf '%s\n' "$1" | install -m 0644 /dev/stdin "$status"; }
trap 'rc=$?; if [ "$rc" -ne 0 ]; then report "SJERP BUSINESS SETUP FAILED (exit $rc)"; fi' EXIT
report 'SJERP business acceptance setup in progress'
address=$(ip -4 -o addr show scope global dev eth0 | awk 'NR == 1 {split($4, a, "/"); print a[1]}')
test -n "$address"
nginx=/etc/nginx/conf.d/sjerp-a.conf
sed -i -E "s/listen 172\.20\.[0-9]+\.[0-9]+:18443 ssl;/listen $address:18443 ssl;/" "$nginx"
nginx -t
systemctl restart nginx
base=/srv/sjerp/current
install -d -m 0700 -o erpverify -g erpverify /run/sjerp-lan-verify
test ! -e /run/sjerp-lan-verify/credentials.json
# Django reads the same isolated runtime target. Do not print or put the password in command arguments.
export SJERP_CAPTURE_CREDENTIALS=/run/sjerp-lan-verify/credentials.json
set -a
. /etc/sjerp/a/runtime.env
set +a
cd "$base/release/backend"
"$base/venv/bin/python" manage.py shell -c '
import json, os, pwd, secrets
from django.contrib.auth import get_user_model
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("select current_database(), current_user")
    assert cursor.fetchone() == ("sjerp_a", "sjerp_a_runtime")
User = get_user_model()
if User.objects.exclude(username="codex").exists():
    raise SystemExit("验收库已有其他用户")
password = secrets.token_urlsafe(36)
user, _ = User.objects.get_or_create(username="codex")
user.is_staff = user.is_superuser = user.is_active = True
user.first_name = "codex"
user.set_password(password)
user.save()
path = os.environ["SJERP_CAPTURE_CREDENTIALS"]
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, "w") as output:
    json.dump({"username": user.username, "password": password}, output)
    account = pwd.getpwnam("erpverify")
    os.fchown(output.fileno(), account.pw_uid, account.pw_gid)
'
cat > /run/systemd/system/sjerp-lan-test-restart.path <<'EOF'
[Unit]
Description=One-shot ERP restart for isolated LAN acceptance
[Path]
PathExists=/run/sjerp-lan-verify/restart.request
Unit=sjerp-lan-test-restart.service
EOF
cat > /run/systemd/system/sjerp-lan-test-restart.service <<'EOF'
[Unit]
Description=One-shot ERP restart for isolated LAN acceptance
[Service]
Type=oneshot
ExecStart=/usr/bin/systemctl stop sjerp-lan-test-restart.path
ExecStart=/usr/bin/rm -f -- /run/sjerp-lan-verify/restart.request
ExecStart=/usr/bin/systemctl restart sjerp-local@a.service
EOF
systemctl daemon-reload
systemctl start sjerp-lan-test-restart.path
report "SJERP BUSINESS SETUP READY: IPv4=$address"
