#!/bin/sh
set -eu
umask 077
[ "$(id -u)" = 0 ] && [ "$(hostname -s)" = sjerp-image-test ] || exit 1

root=/srv/sjerp
sha=96276dffa07c11fb60720a439269df8c36031f7a
version="$root/versions/$sha"
config=/etc/sjerp/a
media=/var/lib/sjerp/a/private-media
disk=/var/lib/sjerp/a/media.ext4
status=/etc/issue.d/91-sjerp-activation.issue
unit=sjerp-local@a.service
report() {
    install -d -m 0755 /etc/issue.d
    printf '%s\n' "$1" | install -m 0644 /dev/stdin "$status"
}
trap 'rc=$?; if [ "$rc" -ne 0 ]; then report "SJERP ACTIVATION FAILED (exit $rc)"; fi' EXIT
report 'SJERP activation in progress'
test "$(cat "$version/READY")" = bb244bba90ecacf21f3835271321592a98292d2549f925c4fbea15726038437c
for path in "$root/current" "$config" "$media" "$disk" /etc/systemd/system/sjerp-local@.service /etc/nginx/conf.d/sjerp-a.conf; do
    if [ -e "$path" ] || [ -L "$path" ]; then echo "安装目标已存在：$path"; exit 1; fi
done
if getent passwd sjerp-a >/dev/null; then echo '运行账号已存在'; exit 1; fi
psql_as_postgres() {
    runuser -u postgres -- /usr/lib/postgresql/17/bin/psql -X -q -v ON_ERROR_STOP=1 "$@"
}
test -z "$(psql_as_postgres -Atd postgres -c "SELECT datname FROM pg_database WHERE datname='sjerp_a'")"
test -z "$(psql_as_postgres -Atd postgres -c "SELECT rolname FROM pg_roles WHERE rolname IN ('sjerp_a_migrate','sjerp_a_runtime')")"
useradd --system --user-group --no-create-home --shell /usr/sbin/nologin sjerp-a
install -d -m 0750 -o root -g sjerp-a "$config"
install -d -m 0755 "$media"
truncate -s 256M "$disk"
mkfs.ext4 -q -F "$disk"
mount_unit=$(systemd-escape --path --suffix=mount "$media")
cat > "/etc/systemd/system/$mount_unit" <<EOF
[Unit]
Description=SJERP private media
[Mount]
What=$disk
Where=$media
Type=ext4
Options=loop,nodev,nosuid,noexec
[Install]
WantedBy=local-fs.target
EOF
systemctl daemon-reload
systemctl enable --now "$mount_unit"
chown sjerp-a:sjerp-a "$media"
chmod 0700 "$media"

migration_password=$(openssl rand -hex 32)
runtime_password=$(openssl rand -hex 32)
secret=$(openssl rand -hex 48)
psql_as_postgres -d postgres <<EOF
CREATE ROLE sjerp_a_migrate LOGIN PASSWORD '$migration_password';
CREATE ROLE sjerp_a_runtime LOGIN PASSWORD '$runtime_password';
CREATE DATABASE sjerp_a OWNER sjerp_a_migrate;
REVOKE ALL ON DATABASE sjerp_a FROM PUBLIC;
GRANT CONNECT ON DATABASE sjerp_a TO sjerp_a_runtime;
EOF
printf '127.0.0.1:5432:sjerp_a:sjerp_a_migrate:%s\n' "$migration_password" > "$config/migration.pgpass"
printf '127.0.0.1:5432:sjerp_a:sjerp_a_runtime:%s\n' "$runtime_password" > "$config/runtime.pgpass"
chown sjerp-a:sjerp-a "$config/runtime.pgpass"
chmod 0600 "$config/"*.pgpass
cat > "$config/runtime.env" <<EOF
APP_STAGE=staging
DJANGO_ALLOWED_HOSTS=localhost
DJANGO_SECRET_KEY=$secret
DATABASE_URL=postgresql://sjerp_a_runtime@127.0.0.1:5432/sjerp_a?connect_timeout=5
PGPASSFILE=$config/runtime.pgpass
MEDIA_ROOT=$media
SJERP_EXPECTED_MEDIA_ROOT=$media
SJERP_EXPECTED_DB_HOST=127.0.0.1
SJERP_EXPECTED_DB_PORT=5432
SJERP_EXPECTED_DB_NAME=sjerp_a
SJERP_EXPECTED_DB_USER=sjerp_a_runtime
SJERP_HTTP_HOST=localhost
SJERP_HTTP_PORT=18131
EOF

backend="$version/release/backend"
examples="$version/release/docs/deployment"
python="$version/venv/bin/python"
(
    cd "$backend"
    export APP_STAGE=staging DJANGO_ALLOWED_HOSTS=localhost DJANGO_SECRET_KEY="$secret" MEDIA_ROOT="$media"
    export DATABASE_URL=postgresql://sjerp_a_migrate@127.0.0.1:5432/sjerp_a PGPASSFILE="$config/migration.pgpass"
    "$python" manage.py migrate --noinput
    "$python" manage.py check
)
psql_as_postgres -d sjerp_a <<'EOF'
GRANT USAGE ON SCHEMA public TO sjerp_a_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sjerp_a_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sjerp_a_runtime;
REVOKE INSERT, UPDATE, DELETE ON django_migrations FROM sjerp_a_runtime;
REVOKE UPDATE, DELETE, TRUNCATE ON crm_operationlog FROM sjerp_a_runtime, PUBLIC;
GRANT EXECUTE ON FUNCTION pg_control_system() TO sjerp_a_migrate;
EOF
chmod 0755 "$root/versions" "$version"
chmod -R a+rX "$version/release" "$version/venv"
ln -s "$version" "$root/current"
install -m 0640 -o root -g sjerp-a "$examples/sjerp-local-gunicorn.conf.py.example" "$config/gunicorn.conf.py"
sed -e "s|/srv/sjerp/%i|$root/current|g" \
    -e "/^\[Unit\]/a RequiresMountsFor=$media\nAfter=postgresql@17-main.service\nRequires=postgresql@17-main.service" \
    -e '/^\[Service\]/a Restart=on-failure\nRestartSec=2' "$examples/sjerp-local@.service.example" > /etc/systemd/system/sjerp-local@.service
printf '\n[Install]\nWantedBy=multi-user.target\n' >> /etc/systemd/system/sjerp-local@.service
chmod 0644 /etc/systemd/system/sjerp-local@.service

openssl req -x509 -newkey rsa:2048 -nodes -days 7 -subj /CN=localhost -addext subjectAltName=DNS:localhost \
    -keyout "$config/https.key" -out "$config/https.crt"
install -m 0644 "$config/https.crt" /etc/sjerp-a-test-ca.crt
sed -n '/^    listen 443 ssl;/,$p' "$examples/operations-nginx.conf.example" | sed \
    -e '1i server {' \
    -e 's/listen 443 ssl;/listen 127.0.0.1:18443 ssl;/' \
    -e 's/erp.example.invalid/localhost/g' \
    -e "s|/etc/sunjack/tls/fullchain.pem|$config/https.crt|" \
    -e "s|/etc/sunjack/tls/privkey.pem|$config/https.key|" \
    -e "s|/srv/sunjack/frontend/dist|$root/current/release/frontend/dist|" \
    -e 's|127.0.0.1:8000|127.0.0.1:18131|' > /etc/nginx/conf.d/sjerp-a.conf
chmod 0644 /etc/nginx/conf.d/sjerp-a.conf
nginx -t
systemctl daemon-reload
systemctl enable --now "$unit"
systemctl reload nginx
curl -fsS --cacert /etc/sjerp-a-test-ca.crt https://localhost:18443/ >/dev/null
headers=$(mktemp)
curl -fsS --cacert /etc/sjerp-a-test-ca.crt -D "$headers" https://localhost:18443/api/session/csrf/ >/dev/null
grep -qi '^set-cookie: csrftoken=' "$headers"
rm -f "$headers"
report 'SJERP ACTIVATION READY: dedicated PostgreSQL and HTTPS verified'
